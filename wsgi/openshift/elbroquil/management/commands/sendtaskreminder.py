# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
import elbroquil.models as models
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ObjectDoesNotExist
import html2text
from datetime import date, datetime, timedelta

import elbroquil.libraries as libs

class Command(BaseCommand):
    help = 'Envia el correo recordatorio a los miembros que tienen permanencia cada semana'

    def handle(self, *args, **options):
        self.stdout.write('Enviando el recordatorio a los responsables de permanencia...')
        
            
        # Check if there is a distribution task in the following 9 days (larger margin to handle modified dist. dates)
        now = libs.get_now()
        some_days_later = now + timedelta(days=9)
        tasks = models.DistributionTask.objects.filter(distribution_date__lt = some_days_later, distribution_date__gt = now).prefetch_related('user', 'user__extrainfo')
        
        if tasks.count() == 0:
            self.stdout.write('No hay permanencias en los proximos dias, no se enviara ningun correo...')
            return
        
        task_date = tasks.first().distribution_date
        
        # Send the reminder email to the active members
        email_subject = '[BroquilGotic]Recordatori de Permanències'
        html_content = "Hola,<br/>\
        <br/>\
        Us recordem que el dia " + task_date.strftime('%d/%m/%Y') + " us toca perman&egrave;ncia.<br/>\
        Adjunto <a href='https://docs.google.com/document/d/1HiO933Eh_00ftbK8qTpBv09OKTkcIIqD4IdRov1qxhA/edit'> manual d'instruccions</a> i <a href='https://vimeo.com/117321849'>video explicatiu</a> per si de cas els voleu mirar abans de venir.<br/>\
        <br/>\
        En cas que no pogueu venir poseu-vos en contacte amb la resta de broquilaires per demanar una permuta <a href='https://groups.google.com/forum/#!forum/elbroquildelgotic'>aqu&iacute;</a>.<br/>\
        <br/>\
        Si no teniu clau de La Negreta aviseu per poder quedar abans i donar-vos-la.<br/>\
        <br/>\
        Si el mateix dimecres teniu cap dubte o problema truqueu-me, jo estar&eacute; pel barri. O poseu-vos en contacte amb alguna altra persona de la Comissi&oacute; de Perman&egrave;ncies.<br/>\
        <br/>\
        A reveure i Salut!"
        
        # If there is an email template stored in DB, use it
        email = models.EmailTemplate.objects.filter(email_code=models.EMAIL_TASK_REMINDER).first()
        
        if email:
            self.stdout.write('RECORDATORIO email plantilla encontrada en el base de datos.')
            email_subject = email.full_subject()
            html_content = email.body
            
        to = []
        cc = []
        
        # Add the email addresses for members that have a task this week
        for task in tasks:
            to.append(task.user.email)

            # Try to see if there is a second email address for the user and add it if necessary
            try:
                if task.user.extrainfo.secondary_email and len(task.user.extrainfo.secondary_email) > 0:
                    to.append(task.user.extrainfo.secondary_email)
            except ObjectDoesNotExist:
                pass
        
        cc_lists = models.EmailList.objects.filter(cc_task_reminders=True)

        # For all CC lists, add the email addresses to CC
        for cc_list in cc_lists:
            for email_address in cc_list.email_addresses.replace(' ',',').split(','):
                if email_address != "":
                    cc.append(email_address)
        
        libs.send_email_with_cc(email_subject, html_content, to, cc)
        
        self.stdout.write('RECORDATORIO email enviado a %d personas.' % len(to))