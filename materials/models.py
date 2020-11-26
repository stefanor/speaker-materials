from django.db.models import (
    CASCADE, RESTRICT, CharField, DateTimeField, ForeignKey, IntegerField,
    Model, TextChoices, TextField)
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from materials import get_event_model
from materials.core import Material, get_material


class UploadStates(TextChoices):
    CREATED = 'CREATED', _('Created')
    UPLOADED = 'UPLOADED', _('Uploaded')
    DELETED = 'DELETED', _('Deleted')


class Upload(Model):
    id: int
    event: ForeignKey = ForeignKey(get_event_model(), on_delete=RESTRICT)
    material_id: CharField = CharField(max_length=32)
    filename: CharField = CharField(max_length=128)
    sha256: CharField = CharField(max_length=64, blank=True, null=True)
    size: IntegerField = IntegerField()
    uploader: ForeignKey = ForeignKey(get_user_model(), on_delete=RESTRICT,
                                      blank=True, null=True)  # FIXME: auth
    created: DateTimeField = DateTimeField(auto_now_add=True)
    updated: DateTimeField = DateTimeField(auto_now=True)
    uploaded: DateTimeField = DateTimeField(blank=True, null=True)
    deleted: DateTimeField = DateTimeField(blank=True, null=True)

    @property
    def state(self) -> str:
        if self.deleted:
            return UploadStates.DELETED
        if self.uploaded:
            return UploadStates.UPLOADED
        return UploadStates.CREATED

    @property
    def material(self) -> Material:
        return get_material(self.material_id)

    @property
    def storage_path(self) -> str:
        extension = self.filename.rsplit('.', 1)[-1]
        return f'{self.event.slug}-{self.material_id}-{self.id}.{extension}'


class Review(Model):
    class Actions(TextChoices):
        ACCEPT = 'A', _('Accept')
        COMMENT = 'C', _('Comment')
        REJECT = 'R', _('Reject')

    upload: ForeignKey = ForeignKey(Upload, on_delete=CASCADE)
    action: CharField = CharField(max_length=1, choices=Actions.choices)
    comment: TextField = TextField(blank=True)
    reviewer: ForeignKey = ForeignKey(get_user_model(), on_delete=RESTRICT)
    created: DateTimeField = DateTimeField(auto_now_add=True)
    updated: DateTimeField = DateTimeField(auto_now=True)
