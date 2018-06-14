# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from elbroquil.tasks import send_sunday_reminder


class Command(BaseCommand):
    help = 'Envia el correo recordatorio a los miembros activos'

    def handle(self, *args, **options):
        send_sunday_reminder()
