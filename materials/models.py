from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from materials import get_event_model


class UploadStates(models.TextChoices):
    CREATED = 'CREATED', _('Created')
    UPLOADED = 'UPLOADED', _('Uploaded')
    DELETED = 'DELETED', _('Deleted')


class Upload(models.Model):
    event = models.ForeignKey(get_event_model(), on_delete=models.RESTRICT)
    material = models.CharField(max_length=32)
    filename = models.CharField(max_length=128)
    sha256 = models.CharField(max_length=64, blank=True, null=True)
    size = models.IntegerField()
    uploader = models.ForeignKey(get_user_model(), on_delete=models.RESTRICT,
                                 blank=True, null=True)  # FIXME: auth
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    uploaded = models.DateTimeField(blank=True, null=True)
    deleted = models.DateTimeField(blank=True, null=True)

    @property
    def state(self):
        if self.deleted:
            return UploadStates.DELETED
        if self.uploaded:
            return UploadStates.UPLOADED
        return UploadStates.CREATED

    @property
    def material_name(self):
        return settings.MATERIALS[self.material]['name']

    @property
    def storage_path(self):
        extension = self.filename.rsplit('.', 1)[-1]
        return f'{self.event.slug}-{self.material}-{self.id}.{extension}'


class Review(models.Model):
    class Actions(models.TextChoices):
        ACCEPT = 'A', _('Accept')
        COMMENT = 'C', _('Comment')
        REJECT = 'R', _('Reject')

    upload = models.ForeignKey(Upload, on_delete=models.CASCADE)
    action = models.CharField(max_length=1, choices=Actions.choices)
    comment = models.TextField(blank=True)
    reviewer = models.ForeignKey(get_user_model(), on_delete=models.RESTRICT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
