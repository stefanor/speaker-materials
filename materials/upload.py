from dataclasses import dataclass
from hashlib import sha256
from itertools import count
from tempfile import TemporaryFile

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from materials.models import Upload, UploadStates
from materials.storage import get_chunk_path, get_storage, get_temp_storage


@dataclass
class ResumableRequest:
    chunk_number: int  # resumableChunkNumber - chunk index (1-indexed)
    chunk_size: int  # resumableChunkSize - typical chunk size in bytes
    total_size: int  # resumableTotalSize - total file size in bytes
    total_chunks: int  # resumableTotalChunks - total number of chunks
    id: str  # resumableIdentifier - unique identifier
    filename: str  # resumableFilename - original file name
    relative_path: str  # resumableRelativePath - original relative path

    @classmethod
    def parse_query_string(cls, GET):
        return cls(
            chunk_number=int(GET['resumableChunkNumber']),
            chunk_size=int(GET['resumableChunkSize']),
            total_size=int(GET['resumableTotalSize']),
            total_chunks=int(GET['resumableTotalChunks']),
            id=GET['resumableIdentifier'],
            filename=GET['resumableFilename'],
            relative_path=GET['resumableRelativePath'],
        )


class ResumableUpload:
    upload: Upload

    def __init__(self, upload):
        self.upload = upload

    @classmethod
    def from_query_string(cls, request, event):
        """Create a ResumableUpload from a resumable.js request"""
        r_req = ResumableRequest.parse_query_string(request.GET)
        upload = Upload.objects.get(id=r_req.id, event=event)
        if upload.state != UploadStates.CREATED:
            raise PermissionDenied(
                f'Upload is in state {upload.state}, not CREATED')
        return ResumableUpload(upload)

    def chunk_exists(self, request):
        """Was the specified chunk received?"""
        r_req = ResumableRequest.parse_query_string(request.GET)
        target_path = self.get_req_chunk_path(r_req)
        storage = get_temp_storage()
        if storage.exists(target_path):
            if storage.size(target_path) == r_req.chunk_size:
                return True
        return False

    def save_chunk(self, request):
        """Save a chunk to our temporary storage"""
        r_req = ResumableRequest.parse_query_string(request.GET)
        target_path = self.get_req_chunk_path(r_req)
        temp_storage = get_temp_storage()
        if temp_storage.exists(target_path):
            temp_storage.delete(target_path)

        if len(request.FILES) != 1:
            raise PermissionDenied("Exactly one file will be accepted")
        temp_storage.save(target_path, next(request.FILES.values()))

    def complete_upload(self):
        temp_storage = get_temp_storage()
        storage = get_storage()
        upload = self.upload
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

        self.delete_upload_chunks()

    def delete_upload_chunks(self):
        temp_storage = get_temp_storage()
        for chunk in count(1):
            path = get_chunk_path(self.upload, chunk)
            if temp_storage.exists(path):
                temp_storage.delete(path)
            else:
                break

    def get_req_chunk_path(self, r_req):
        if r_req.total_size != self.upload.size:
            raise PermissionDenied("Size mismatch")
        if max(r_req.chunk_number, r_req.total_chunks) > 9999:
            raise PermissionDenied("Chunks are too small")
        return get_chunk_path(self.upload, r_req.chunk_number)
