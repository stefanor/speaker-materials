from xml.etree import ElementTree

from django.core.management.base import BaseCommand

import requests

from standalone.models import Event


class Command(BaseCommand):
    help = 'Import a schedule from Pentabarf XML'

    def add_arguments(self, parser):
        parser.add_argument('url', help='Pentabarf XML feed URL')

    def handle(self, *args, **options):
        with requests.get(options['url']) as r:
            tree = ElementTree.fromstring(r.content)

        for event in tree.findall('.//event'):
            conf_url = event.findtext('conf_url')
            slug = conf_url.strip('/').rsplit('/', 1)[-1]
            Event.objects.update_or_create(
                slug=slug,
                defaults={'title': event.findtext('title')})
