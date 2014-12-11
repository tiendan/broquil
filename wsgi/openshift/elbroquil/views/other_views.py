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
    
    
def test_email(request):
    email_subject = '[BroquilGotic]Oferta d\'aquesta setmana'
    

    html_content = """<p>Thanks <a href="https://github.com/tiendan" class="user-mention">@tiendan</a>! I'm sure you noticed, but I fixed some small issues with this script in <a href="http://el-broquil.rhcloud.com" class="commit-link"><tt>dfdbece</tt></a> so you'll want to include that as well.</p>"""
    
    # Add the Gmail action link (yet to see if it works)
    html_content += """<div itemscope itemtype="http://schema.org/EmailMessage">
    <div itemprop="action" itemscope itemtype="http://schema.org/ViewAction">
    <link itemprop="url" href="http://el-broquil.rhcloud.com"></link>
    <meta itemprop="name" content="Fer Comanda"></meta>
    </div>
    <meta itemprop="description" content="Fer Comanda"></meta>
    </div>"""
    
    result = libs.send_email_to_address(email_subject, html_content, ["yalanim@gmail.com"])
