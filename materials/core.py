from collections import OrderedDict
from typing import List

from django.conf import settings

materials: 'OrderedDict[str, Material]' = OrderedDict()


class Material:
    """A Material, defined in settings"""
    id: str
    name: str
    extensions: List[str]
    validators: List[str]

    def __init__(self, material_dict):
        self.id = material_dict['id']
        self.name = material_dict['name']
        self.extensions = material_dict['extensions']
        self.validators = material_dict['validators']


def load_materials():
    global materials
    for material_dict in settings.MATERIALS:
        material = Material(material_dict)
        materials[material.id] = material


def get_material(material_id: str) -> Material:
    return materials[material_id]
