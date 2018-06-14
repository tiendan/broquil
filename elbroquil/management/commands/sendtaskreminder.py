# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from elbroquil.tasks import send_task_reminder


class Command(BaseCommand):
    help = """Envia el correo recordatorio a los miembros que tienen """ \
           """permanencia cada semana"""

    def handle(self, *args, **options):
        send_task_reminder()
