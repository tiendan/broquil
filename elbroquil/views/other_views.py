# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import translation
from django.utils.translation import ugettext as _, check_for_language, get_language_from_request, activate, get_language
from django.core.urlresolvers import resolve, Resolver404

import elbroquil.libraries as libs
import elbroquil.models as models
from elbroquil.tasks import send_order_to_producers

import html2text


def set_language(request):
    """
    Set the language for the current session.
    """
    from django.conf import settings
    from django.http import HttpResponseRedirect, JsonResponse
    from django.views.decorators.http import require_POST
    
    if request.method == 'POST':
        user_language = request.POST.get('language', '')
    else:
        user_language = request.GET.get('language', '')
    
    # If no language is provided, use the default
    if not user_language:
        user_language = settings.LANGUAGE_CODE
    
    # Validate that the language is in our LANGUAGES setting
    if user_language and check_for_language(user_language):
        # Store the current language to check if it's changing
        current_language = get_language_from_request(request)
        
        # Check if there's a next parameter
        next_url = request.POST.get('next', request.GET.get('next', None))
        
        # If no next parameter, try to get the referer
        if not next_url:
            next_url = request.META.get('HTTP_REFERER', None)
        
        view_name = None
        args = None
        kwargs = None
        
        # If we have a URL and the language is changing, try to resolve it
        if next_url and current_language != user_language:
            try:
                # Remove the domain part if present
                if next_url.startswith('http'):
                    from urllib.parse import urlparse
                    parsed_url = urlparse(next_url)
                    next_url = parsed_url.path
                    if parsed_url.query:
                        next_url += '?' + parsed_url.query
                
                # Try to resolve the URL to its view
                resolved = resolve(next_url)
                
                # If we can resolve it, generate the URL in the new language
                if resolved:
                    # Get the view name and arguments
                    view_name = resolved.view_name
                    args = resolved.args
                    kwargs = resolved.kwargs
            except Resolver404:
                # If we can't resolve the URL, keep the original
                pass
        
        # Activate the new language
        translation.activate(user_language)
        
        # Set the language in the session
        request.session['django_language'] = user_language
        
        # Force the session to be saved
        request.session.modified = True
        
        # Generate the URL in the new language
        if view_name is not None:
            try:
                next_url = reverse(view_name, args=args, kwargs=kwargs)
            except:
                # If we can't generate the URL, keep the original
                pass
        # If still no redirect URL, use the site root
        if not next_url:
            next_url = reverse('site_root')
            
        response = HttpResponseRedirect(next_url)
        response.set_cookie('django_language', user_language, max_age=365*24*60*60)  # 1 year
        return response
    
    return HttpResponseRedirect(reverse('site_root'))


@login_required
def contact(request):
    result_message = None
    distribution_details = models.DistributionAccountDetail.objects.all(
    ).order_by("-date")[:4]
    to_lists = models.EmailList.objects.all().order_by("name")

    if request.method == 'POST':
        to_list = int(request.POST.get("to-list").strip())
        incident_date = request.POST.get("date").strip()
        message = request.POST.get("message").strip()

        # If selected list value is -1, it is an incident email
        if to_list == -1:
            cc_lists = models.EmailList.objects.filter(cc_incidents=True)
            incident_date_formatted = incident_date[
                8:10] + "/" + incident_date[5:7] + "/" + incident_date[0:4]

            subject = "[BroquilGotic] Incidencia dia " + \
                incident_date_formatted
            content = html2text.html2text(message)
            to = []
            cc = []

            # Find the people who had distribution task for the selected date,
            # and add them to TO list
            distribution_tasks = models.DistributionTask.objects.filter(
                distribution_date=incident_date) \
                .prefetch_related('user', 'user__extrainfo')

            for task in distribution_tasks:
                to.append(task.user.email)

                # Try to see if there is a second email address for the user
                # and add it if necessary
                try:
                    if task.user.extrainfo.secondary_email \
                       and len(task.user.extrainfo.secondary_email) > 0:
                        to.append(task.user.extrainfo.secondary_email)
                except ObjectDoesNotExist:
                    pass

            # For all CC lists, add the email addresses to CC
            for cc_list in cc_lists:
                for email_address in cc_list.email_addresses \
                        .replace(' ', ',').split(','):
                    if email_address != "":
                        cc.append(email_address)

            # Add the user who sent this message to the CC
            cc.append(request.user.email)

            # Send the email
            libs.send_email_with_cc(subject, content, to, cc)
        # Else it is an email to a specific comission
        else:
            selected_list = models.EmailList.objects.get(pk=to_list)

            subject = "[BroquilGotic] Missatge a " + selected_list.name
            content = html2text.html2text(message)
            to = []
            cc = []

            for email_address in selected_list.email_addresses.replace(' ', ',').split(','):
                if email_address != "":
                    to.append(email_address)

            # Add the user who sent this message to the CC
            cc.append(request.user.email)

            # Send the email
            libs.send_email_with_cc(subject, content, to, cc)

        result_message = _(
            "Message sent successfully and a copy is sent to your address.")

    # Store latest few dates in variable
    date_texts = []
    date_values = []

    for detail in distribution_details:
        date_texts.append(detail.date)
        date_values.append(detail.date.strftime("%Y-%m-%d"))

    distribution_dates = list(zip(date_texts, date_values))

    return render(request, 'contact.html', {
        'to_lists': to_lists,
        'last_distribution_dates': distribution_dates,
        'result_message': result_message,
    })


def producer_info(request, producer_id=''):
    producers = []
    single_producer = False

    if producer_id == '':
        producers = models.Producer.objects.filter(active=True).order_by("pk")
    else:
        producers = models.Producer.objects.filter(pk=int(producer_id))
        single_producer = True

    return render(request, 'producer/producer_info.html', {
        'producers': producers,
        'single_producer': single_producer,
    })


def tasks(request):
    send_order_to_producers()
    return HttpResponse('OK')
