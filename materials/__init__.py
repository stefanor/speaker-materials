from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


default_app_config = 'materials.apps.MaterialsConfig'


class EventInterface():
    """
    Interface to implement for settings.MATERIALS_EVENT_MODEL
    Would be an ABC if django models didn't already have a metaclass.
    """
    @property
    def title(self):
        return 'Event Title'

    @property
    def slug(self):
        return 'event-slug'


def get_event_model():
    """
    Return the Event model for this project.
    """
    name = settings.MATERIALS_EVENT_MODEL
    try:
        model = django_apps.get_model(name, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured(
            "MATERIALS_EVENT_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            f"MATERIALS_EVENT_MODEL refers to model '{name} that has not been "
            "installed")
    return model
