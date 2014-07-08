from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'elbroquil.views.view_order', name='site_root'),
    url(_(r'^about/'), TemplateView.as_view(template_name="about.html"), name='about'),
    url(_(r'^perma/([0-9]+)/$'), 'elbroquil.views.view_product_orders', name='view_product_orders'),
    url(_(r'^perma/$'), 'elbroquil.views.view_order_totals', name='view_order_totals'),
    url(_(r'^order/([0-9]+)/$'), 'elbroquil.views.update_order', name='update_order'),
    url(_(r'^order/$'), 'elbroquil.views.view_order', name='view_order'),
    url(_(r'^products/confirm'), 'elbroquil.views.confirm_products', name='confirm_products'),
    url(_(r'^products/check'), 'elbroquil.views.check_products', name='check_products'),
    url(_(r'^products/$'), 'elbroquil.views.upload_products', name='upload_products'),
    url(r'^admin/', include(admin.site.urls)),
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    url(r'^rosetta/', include('rosetta.urls')),
    #(r'^i18n/', include('django.conf.urls.i18n')),
    url(_(r'^setlang/$'), 'elbroquil.views.set_language', name='set_language'),
)
