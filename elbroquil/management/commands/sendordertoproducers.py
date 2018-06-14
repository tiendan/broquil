# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from elbroquil.tasks import send_order_to_producers


class Command(BaseCommand):
    help = 'Envia el pedido total al productor'

    def handle(self, *args, **options):
        send_order_to_producers()
