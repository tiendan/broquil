# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
import elbroquil.models as models
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ObjectDoesNotExist
import html2text

import elbroquil.libraries as libs

class Command(BaseCommand):
    help = 'Envia el correo recordatorio a los miembros activos'

    def handle(self, *args, **options):
        self.stdout.write('Enviando el recordatoria a los miembros...')
    
        # Send the reminder email to the active members
        email_subject = '[BroquilGotic]No t\'oblidis de fer la comanda'
        html_content = "Hola broquilire!!!!<br/>\
        <br/>\
        Tant sols recordar-te que pots fer la comanda fins el Diumenge nit <a href=\"http://127.0.0.1:8000/\">aqu&iacute;</a> i que pots recullir la comanda el <em>Dimecres</em> de <strong>18 a 19:30</strong>, no ho deixis correr ;)<br/>\
        <br/>\
        Tamb&eacute;  que necessitem que t'apuntis a les permanencies en el sistema :P<br/>\
        <br/>\
        Salut!! amb el broquil :P<br/>"
        
        # If there is an email template stored in DB, use it
        email = models.EmailTemplate.objects.filter(email_code=models.EMAIL_REMINDER).first()
        
        if email:
            self.stdout.write('RECORDATORIO email plantilla encontrada en el base de datos.')
            email_subject = email.full_subject()
            html_content = email.body
        
        result = libs.send_email_to_active_users(email_subject, html_content)
        
        self.stdout.write('RECORDATORIO email enviado a %d personas.' % result[0])