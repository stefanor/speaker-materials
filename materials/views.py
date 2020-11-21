from django.conf import settings
from django.views.generic import DetailView, ListView

from materials import get_event_model
from materials.models import Upload


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
                    material=material['name'])
            except Upload.DoesNotExist:
                material['upload'] = None
            current_uploads.append(material)

        context['current_uploads'] = current_uploads
        context['deleted_uploads'] = Upload.objects.filter(
            event=event).exclude(deleted__isnull=True).order_by('-created')
        return context
