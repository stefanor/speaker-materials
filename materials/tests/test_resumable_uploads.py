from io import BytesIO
from urllib.parse import urlencode

from django.test import Client

from materials import get_event_model
from materials.models import Upload
from materials.tests.support import MockStorageTestCase
from materials.storage import get_chunk_path, get_temp_storage


def make_args(**override):
    args = {
        'resumableIdentifier': 'id',
        'resumableChunkNumber': 1,
        'resumableChunkSize': 1024,
        'resumableTotalSize': 1024,
        'resumableTotalChunks': 1,
        'resumableFilename': 'test.bin',
        'resumableRelativePath': './test.bin',
    }
    args.update(override)
    return urlencode(args)


class SingleChunkTestCase(MockStorageTestCase):
    def setUp(self):
        super().setUp()
        get_event_model().objects.create(title='test', slug='test')

    def test_upload(self):
        c = Client()
        r = c.post('/events/test/upload/slides',
                   {'action': 'create', 'filename': 'test.pdf', 'size': 1024})
        self.assertEqual(r.status_code, 201)
        identifier = r.json()['identifier']
        self.assertTrue(identifier)

        r = c.post('/events/test/upload/slides?'
                   + make_args(resumableIdentifier=identifier),
                   {'file': BytesIO(b'\xde\xad\xbe\xef' * 256)})
        self.assertEqual(r.status_code, 201)
        r = c.post('/events/test/upload/slides',
                   {'action': 'complete', 'identifier': identifier})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json()['sha256'],
            '326e228882b798cecdd5fb44fddc9a7f843014a517611a71bcc6b3c838cf9e7f')


class ChunkTestCase(MockStorageTestCase):
    def setUp(self):
        super().setUp()
        self.event = get_event_model().objects.create(title='test', slug='test')
        self.upload = Upload.objects.create(
            event=self.event, material_id='slides', filename='test.pdf',
            size=1024)
        self.args = make_args(resumableIdentifier=self.upload.id)

    def complete(self):
        c = Client()
        r = c.post('/events/test/upload/slides',
                   {'action': 'complete', 'identifier': self.upload.id})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.json()['sha256'],
            '326e228882b798cecdd5fb44fddc9a7f843014a517611a71bcc6b3c838cf9e7f')

    def test_get_nonexistant(self):
        c = Client()
        r = c.get('/events/test/upload/slides?' + self.args)
        self.assertEqual(r.status_code, 204)

    def test_get_existant(self):
        get_temp_storage().save(
            get_chunk_path(self.upload, 1),
            BytesIO(b'\xde\xad\xbe\xef' * 256))
        c = Client()
        r = c.get('/events/test/upload/slides?' + self.args)
        self.assertEqual(r.status_code, 200)

    def test_get_existant_too_small(self):
        get_temp_storage().save(
            get_chunk_path(self.upload, 1),
            BytesIO(b'\xde\xad\xbe\xef' * 255))
        c = Client()
        r = c.get('/events/test/upload/slides?' + self.args)
        self.assertEqual(r.status_code, 204)

    def test_upload_single_chunk(self):
        c = Client()
        r = c.post('/events/test/upload/slides?' + self.args,
                   {'file': BytesIO(b'\xde\xad\xbe\xef' * 256)})
        self.assertEqual(r.status_code, 201)
        self.complete()

    def test_upload_multi_chunk(self):
        c = Client()
        for i in range(4):
            args = make_args(resumableIdentifier=self.upload.id,
                             resumableChunkSize=512,
                             resumableChunkNumber=i + 1)
            r = c.post('/events/test/upload/slides?' + args,
                       {'file': BytesIO(b'\xde\xad\xbe\xef' * 64)})
            self.assertEqual(r.status_code, 201)
        self.complete()

    def test_upload_replacement_chunk(self):
        get_temp_storage().save(
            get_chunk_path(self.upload, 1),
            BytesIO(b'\x00\x00\x00\x00' * 255))
        c = Client()
        r = c.post('/events/test/upload/slides?' + self.args,
                   {'file': BytesIO(b'\xde\xad\xbe\xef' * 256)})
        self.assertEqual(r.status_code, 201)
        self.complete()
