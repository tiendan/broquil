# -*- coding: utf-8 -*-
from decimal import Decimal
import ast
import logging      # import the logging library
from datetime import date

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import F, Q, Sum
from django.db import transaction

from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.utils import translation
from django.views.generic import FormView
import elbroquil.libraries as libs

import html2text

import elbroquil.models as models

def set_language(request):
    #current_url = resolve(request.POST.get(next).strip()).url_name
    #logger.error("CURRENT URL")
    #logger.error(current_url)
    
    if request.method == 'POST':
        user_language = request.POST['language'] or 'ca'
    else:
        user_language = request.GET['language'] or 'ca'
    translation.activate(user_language)
    request.session['django_language'] = user_language

    #logger.error("NEXT URL")
    #logger.error(reverse(current_url, args=()))

    return HttpResponseRedirect(reverse('site_root'))
    
    
#def test_email(request):
#    email_subject = '[BroquilGotic]Oferta d\'aquesta setmana'
#    
#
#    html_content = """<p>Thanks <a href="https://github.com/tiendan" class="user-mention">@tiendan</a>! I'm sure you noticed, but I fixed some small issues with this script in <a href="http://el-broquil.rhcloud.com" class="commit-link"><tt>dfdbece</tt></a> so you'll want to include that as well.</p>"""
#    
#    # Add the Gmail action link (yet to see if it works)
#    html_content += """<div itemscope itemtype="http://schema.org/EmailMessage">
#    <div itemprop="action" itemscope itemtype="http://schema.org/ViewAction">
#    <link itemprop="url" href="http://el-broquil.rhcloud.com"></link>
#    <meta itemprop="name" content="Fer Comanda"></meta>
#    </div>
#    <meta itemprop="description" content="Fer Comanda"></meta>
#    </div>"""
#    
#    result = libs.send_email_to_address(email_subject, html_content, ["yalanim@gmail.com"])

@login_required
def contact(request):
    result_message = None
    distribution_details = models.DistributionAccountDetail.objects.all().order_by("-date")[:4]
    to_lists = models.EmailList.objects.all().order_by("name")
    dates = []
    
    if request.method == 'POST':
        to_list = int(request.POST.get("to-list").strip())
        incident_date = request.POST.get("date").strip()
        message = request.POST.get("message").strip()
        
        # If selected list value is -1, it is an incident email
        if to_list == -1:
            cc_lists = models.EmailList.objects.filter(cc_incidents=True)
            incident_date_formatted = incident_date[8:10] + "/" + incident_date[5:7] + "/" + incident_date[0:4]
            
            subject="[BroquilGotic] Incidencia dia " + incident_date_formatted
            content = html2text.html2text(message)
            to = []
            cc = []
            
            # Find the people who had distribution task for the selected date, and add them to TO list
            distribution_tasks = models.DistributionTask.objects.filter(distribution_date=incident_date).prefetch_related('user', 'user__extrainfo')
            
            for task in distribution_tasks:
                to.append(task.user.email)

                # Try to see if there is a second email address for the user and add it if necessary
                try:
                    if task.user.extrainfo.secondary_email and len(task.user.extrainfo.secondary_email) > 0:
                        to.append(task.user.extrainfo.secondary_email)
                except ObjectDoesNotExist:
                    pass
            
            # For all CC lists, add the email addresses to CC
            for cc_list in cc_lists:
                for email_address in cc_list.email_addresses.replace(' ',',').split(','):
                    if email_address != "":
                        cc.append(email_address)
            
            # Add the user who sent this message to the CC
            cc.append(request.user.email)
            
            # Send the email
            libs.send_email_with_cc(subject, content, to, cc)
        # Else it is an email to a specific comission
        else:
            selected_list = models.EmailList.objects.get(pk=to_list)
            
            subject="[BroquilGotic] Missatge a " + selected_list.name
            content = html2text.html2text(message)
            to = []
            cc = []
            
            for email_address in selected_list.email_addresses.replace(' ',',').split(','):
                if email_address != "":
                    to.append(email_address)
            
            # Add the user who sent this message to the CC
            cc.append(request.user.email)
            
            # Send the email
            libs.send_email_with_cc(subject, content, to, cc)
            
        result_message = _("Message sent successfully and a copy is sent to your address.")
    
    
    # Store latest few dates in variable
    date_texts = []
    date_values = []
    
    for detail in distribution_details:
        date_texts.append(detail.date)
        date_values.append(detail.date.strftime("%Y-%m-%d"))
    
    distribution_dates = zip(date_texts, date_values)

    return render(request, 'contact.html', {
        'to_lists': to_lists,
        'last_distribution_dates': distribution_dates,
        'result_message': result_message,
    })