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