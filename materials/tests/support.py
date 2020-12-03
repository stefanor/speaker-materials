from io import BytesIO, StringIO
from typing import Dict

from django.test import TestCase, override_settings
from django.core.files import File
from django.core.files.storage import Storage


class InMemoryStorage(Storage):
    """An in-memory Django storage engine, for use in tests"""

    # Single storage area, used across all instances
    _files: Dict[str, bytes] = {}

    @classmethod
    def wipe(cls):
        cls._files.clear()

    def _open(self, name, mode='rb'):
        if mode.endswith('b'):
            cls = BytesIO
        else:
            cls = StringIO
        fmode = mode.rstrip('btU')
        if fmode == 'r':
            return File(cls(self._files[name]))
        raise NotImplementedError(f'mode: {mode}')

    def _save(self, name, content):
        self._files[name] = content.read()

    def delete(self, name):
        del self._files[name]

    def exists(self, name):
        return name in self._files

    def size(self, name):
        return len(self._files[name])


@override_settings(
    MATERIALS_STORAGE='materials.tests.support.InMemoryStorage',
    MATERIALS_TEMP_STORAGE='materials.tests.support.InMemoryStorage')
class MockStorageTestCase(TestCase):
    def setUp(self):
        InMemoryStorage.wipe()
