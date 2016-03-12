from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _

import elbroquil.views as broquil_views
import django.contrib.auth.views as auth_views

#from django.contrib.auth.views import password_reset_confirm #, password_reset_done, password_reset_complete

admin.autodiscover()

urlpatterns = [
    url(r'^$', broquil_views.view_order, name='site_root'),
    
    url(_(r'^help/'), TemplateView.as_view(template_name="help.html"), name='help'),
    url(_(r'^contact/$'), broquil_views.contact, name='contact'),
    
    # Distribution related URLs
    url(_(r'^dist/$'), broquil_views.view_order_totals, name='view_order_totals'),
    url(_(r'^dist/pdf/$'), broquil_views.download_orders_pdf, name='download_orders_pdf'),
    url(_(r'^dist/cash/$'), broquil_views.count_initial_cash, name='count_initial_cash'),
    url(_(r'^dist/baskets/$'), broquil_views.view_basket_counts, name='view_basket_counts'),
    url(_(r'^dist/([0-9]+)/$'), broquil_views.view_product_orders, name='view_product_orders'),
    url(_(r'^dist/product/([0-9]+)/$'), broquil_views.view_product_orders_with_id, name='view_product_orders_with_id'),
    url(_(r'^dist/payment/$'), broquil_views.member_payment, name='member_payment'),
    url(_(r'^dist/account/$'), broquil_views.account_summary, name='account_summary'),
    
    # Order related URLs
    url(_(r'^order/rate/$'), broquil_views.rate_products, name='rate_products'),
    url(_(r'^order/([0-9]+)/$'), broquil_views.update_order, name='update_order'),
    url(_(r'^order/history$'), broquil_views.order_history, name='order_history'),
    url(_(r'^order/$'), broquil_views.view_order, name='view_order'),
    
    # Product related URLs
    url(_(r'^products/view/(?P<producer_id>[0-9]+)$'), broquil_views.view_products, name='view_products'),
    url(_(r'^products/view/$'), broquil_views.view_products, name='view_products'),
    url(_(r'^products/confirm/$'), broquil_views.confirm_products, name='confirm_products'),
    url(_(r'^products/check/$'), broquil_views.check_products, name='check_products'),
    url(_(r'^products/upload/$'), broquil_views.upload_products, name='upload_products'),
    
    url(_(r'^producer/$'), broquil_views.producer_info, name='producer_info'),
    url(_(r'^producer/(?P<producer_id>[0-9]+)$'), broquil_views.producer_info, name='producer_info'),
    
    # Quarterly fee related URLs
    url(_(r'^fees/create/$'), broquil_views.create_fees, name='create_fees'),
    url(_(r'^fees/view/$'), broquil_views.view_fees, name='view_fees'),
    
    # Management related URLs
    url(_(r'^man/account/$'), broquil_views.view_accounting_detail, name='view_accounting_detail'),
    url(_(r'^man/dist/$'), broquil_views.view_distribution_detail, name='view_distribution_detail'),
    
    # Distribution task information is removed for the GENERIC branch
    #url(_(r'^man/perm/$'), broquil_views.view_distribution_task_information, name='view_distribution_task_information'),
    
    
    # Admin and account URLs
    url(r'^admin/', include(admin.site.urls)),
    
    url(r'^accounts/login/$', auth_views.login, {'template_name': 'login.html'}),
    url(r'^accounts/logout/$', auth_views.logout, {'next_page': '/'}),
    url(r'^accounts/passwordchange/$', auth_views.password_change, {'post_change_redirect': '/'}),
    url(r'^accounts/passwordreset/$', auth_views.password_reset, {'post_reset_redirect': '/'}),
    url(r'^accounts/passwordresetconfirm/(?P<uidb64>.+)/(?P<token>.+)/$', auth_views.password_reset_confirm, {'post_reset_redirect': '/'}),
    
    url(r'^rosetta/', include('rosetta.urls')),
    #(r'^i18n/', include('django.conf.urls.i18n')),
    url(_(r'^setlang/$'), broquil_views.set_language, name='set_language'),
]

