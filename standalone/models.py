from django.db.models import TextField, Model


class Event(Model):
    title: TextField = TextField()
    slug: TextField = TextField()

    class Meta:
        swappable = 'MATERIALS_EVENT_MODEL'
