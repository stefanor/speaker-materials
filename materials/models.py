from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from materials import get_event_model


class Upload(models.Model):
    event = models.ForeignKey(get_event_model(), on_delete=models.RESTRICT)
    material = models.CharField(max_length=32)
    uploader = models.ForeignKey(get_user_model(), on_delete=models.RESTRICT)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deleted = models.DateTimeField(blank=True, null=True)

    @property
    def material_name(self):
        return settings.MATERIALS[self.material]['name']


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
