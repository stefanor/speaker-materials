from itertools import count
from logging import getLogger
from hashlib import sha256
from tempfile import TemporaryFile


from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.generic import DetailView, ListView
from django.views.generic.detail import BaseDetailView

from materials import get_event_model
from materials.models import Upload, UploadStates
from materials.storage import get_chunk_path, get_storage, get_temp_storage


log = getLogger(__name__)


class EventListView(ListView):
    model = get_event_model()
    template_name = 'materials/event_list.html'


class EventDetailView(DetailView):
    model = get_event_model()
    template_name = 'materials/event_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = context['object']
        current_uploads = []
        for mat_set in settings.MATERIALS:
            material = mat_set.copy()
            try:
                material['upload'] = Upload.objects.get(
                    event=event, deleted__isnull=True,
                    material_id=material['id'])
            except Upload.DoesNotExist:
                material['upload'] = None
            current_uploads.append(material)

        context['current_uploads'] = current_uploads
        context['deleted_uploads'] = Upload.objects.filter(
            event=event).exclude(deleted__isnull=True).order_by('-created')
        return context


class ResumableUploadView(BaseDetailView):
    model = get_event_model()

    def dispatch(self, request, *args, **kwargs):
        self.event = self.get_object()
        self.material = self.kwargs['material']
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        """Resumable.js checking if a chunk is already fully uploaded.
        200 = yes, otherwise no.
        """
        target_path = self.get_chunk_path_from_url()
        storage = get_temp_storage()
        if storage.exists(target_path):
            chunk_size = int(self.request.GET['resumableChunkSize'])
            if self.storage.size(target_path) == chunk_size:
                return HttpResponse(status=200)
        # Not 200 but not an error to avoid JS console logging
        return HttpResponse(status=204)

    def post(self, *args, **kwargs):
        # Our Resumable.js wrapper: upload initiation & completion
        action = self.request.POST.get('action')
        if action == 'create':
            return self.create_upload(
                filename=self.request.POST['filename'],
                size=self.request.POST['size'])
        elif action == 'complete':
            return self.complete_upload(self.request.POST['identifier'])
        else:
            return self.save_chunk()

    def create_upload(self, filename, size):
        """Prepare to receive an upload"""
        # TODO validate size against settings

        # Supersede existing uploads
        for upload in Upload.objects.filter(
                    event=self.event,
                    material_id=self.material,
                    deleted__isnull=True):
            if upload.state == UploadStates.CREATED:
                self.delete_upload_chunks(upload)
            upload.deleted = timezone.now()
            upload.save()

        upload = Upload(
            event=self.event,
            material_id=self.material,
            filename=filename,
            size=size,
        )
        upload.save()

        return JsonResponse({
            'identifier': upload.id,
        }, status=201)

    def complete_upload(self, identifier):
        """Combine all the chunks and hash them"""
        upload = Upload.objects.get(id=identifier, event=self.event)
        temp_storage = get_temp_storage()
        storage = get_storage()
        hasher = sha256()
        size = 0
        with TemporaryFile() as temp_f:
            for chunk in count(1):
                path = get_chunk_path(upload, chunk)
                if not temp_storage.exists(path):
                    break
                with temp_storage.open(path, 'rb') as chunk_f:
                    for block in iter(lambda: chunk_f.read(1024*1024), b''):
                        size += len(block)
                        temp_f.write(block)
                        hasher.update(block)

            temp_f.seek(0)
            if size == upload.size:
                storage.save(upload.storage_path, temp_f)
                upload.sha256 = hasher.hexdigest()
                upload.completed = timezone.now()
                upload.save()

        self.delete_upload_chunks(upload)

        return JsonResponse({
            'state': upload.state,
            'sha256': upload.sha256,
        })

    def delete_upload_chunks(self, upload):
        temp_storage = get_temp_storage()
        for chunk in count(1):
            path = get_chunk_path(upload, chunk)
            if temp_storage.exists(path):
                temp_storage.delete(path)
            else:
                break

    def save_chunk(self):
        target_path = self.get_chunk_path_from_url()
        temp_storage = get_temp_storage()
        if temp_storage.exists(target_path):
            temp_storage.delete(target_path)

        if len(self.request.FILES) != 1:
            raise PermissionDenied("Exactly one file will be accepted")
        temp_storage.save(target_path, next(self.request.FILES.values()))

        return HttpResponse(status=201)

    def get_chunk_path_from_url(self):
        GET = self.request.GET

        resumableIdentifier = GET['resumableIdentifier']
        upload = Upload.objects.get(id=resumableIdentifier, event=self.event)
        if upload.state != UploadStates.CREATED:
            raise PermissionDenied(
                f'Upload is in state {upload.state}, not CREATED')

        resumableChunkNumber = int(GET['resumableChunkNumber'])
        resumableTotalSize = int(GET['resumableTotalSize'])
        resumableTotalChunks = int(GET['resumableTotalChunks'])
        if resumableTotalSize != upload.size:
            raise PermissionDenied("Size mismatch")
        if max(resumableChunkNumber, resumableTotalChunks) > 9999:
            raise PermissionDenied("Chunks are too small")
        return get_chunk_path(upload, resumableChunkNumber)
