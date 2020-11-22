from django.conf import settings
from django.core.files.storage import get_storage_class


def get_storage():
    """Storage area for material"""
    return get_storage_class(import_path=settings.MATERIALS_STORAGE)()


def get_temp_storage():
    """Temporary storage area for upload chunks"""
    return get_storage_class(import_path=settings.MATERIALS_TEMP_STORAGE)()


def get_chunk_path(upload, chunk):
    """Temporary chunk filename"""
    return (f'{upload.event.slug}-{upload.material}-{upload.id}-'
            f'{chunk:03}.part')
