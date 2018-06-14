from django.core.management.base import BaseCommand

from elbroquil.tasks import create_offer


class Command(BaseCommand):
    help = 'Crea la oferta y informa los miembros activos'

    def handle(self, *args, **options):
        create_offer()
