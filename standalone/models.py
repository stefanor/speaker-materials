from django.db import models


class Event(models.Model):
    title = models.TextField()
    slug = models.TextField()

    class Meta:
        swappable = 'MATERIALS_EVENT_MODEL'
