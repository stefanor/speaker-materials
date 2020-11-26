from django.apps import AppConfig

from materials.core import load_materials


class MaterialsConfig(AppConfig):
    name = 'materials'

    def ready(self):
        load_materials()
