from logging import getLogger

from django.conf import settings
from django.http.response import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.generic import DetailView, ListView
from django.views.generic.detail import BaseDetailView

from materials import get_event_model
from materials.models import Upload, UploadStates
from materials.upload import ResumableUpload


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
        resumable_upload = ResumableUpload.from_query_string(self.request, self.event)
        if resumable_upload.chunk_exists(self.request):
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
                ResumableUpload(upload).delete_upload_chunks()
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

    def save_chunk(self):
        resumable_upload = ResumableUpload.from_query_string(
            self.request, self.event)
        resumable_upload.save_chunk(self.request)
        return HttpResponse(status=201)

    def complete_upload(self, identifier):
        """Combine all the chunks and hash them"""
        upload = Upload.objects.get(id=identifier, event=self.event)
        resumable_upload = ResumableUpload(upload)
        resumable_upload.complete_upload()
        return JsonResponse({
            'state': upload.state,
            'sha256': upload.sha256,
        }, status=201)
