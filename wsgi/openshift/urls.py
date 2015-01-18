from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _

#from django.contrib.auth.views import password_reset_confirm #, password_reset_done, password_reset_complete

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'elbroquil.views.view_order', name='site_root'),
    
    #url(_(r'^about/'), TemplateView.as_view(template_name="about.html"), name='about'),
    
    # Distribution related URLs
    url(_(r'^dist/cash/$'), 'elbroquil.views.count_initial_cash', name='count_initial_cash'),
    url(_(r'^dist/baskets/$'), 'elbroquil.views.view_basket_counts', name='view_basket_counts'),
    url(_(r'^dist/payment/$'), 'elbroquil.views.member_payment', name='member_payment'),
    url(_(r'^dist/account/$'), 'elbroquil.views.account_summary', name='account_summary'),
    url(_(r'^dist/([0-9]+)/$'), 'elbroquil.views.view_product_orders', name='view_product_orders'),
    url(_(r'^dist/product/([0-9]+)/$'), 'elbroquil.views.view_product_orders_with_id', name='view_product_orders_with_id'),
    url(_(r'^dist/$'), 'elbroquil.views.view_order_totals', name='view_order_totals'),
    
    # Order related URLs
    url(_(r'^order/rate/$'), 'elbroquil.views.rate_products', name='rate_products'),
    url(_(r'^order/([0-9]+)/$'), 'elbroquil.views.update_order', name='update_order'),
    url(_(r'^order/history$'), 'elbroquil.views.order_history', name='order_history'),
    url(_(r'^order/$'), 'elbroquil.views.view_order', name='view_order'),
    
    # Product related URLs
    url(_(r'^products/view/(?P<producer_id>[0-9]+)$'), 'elbroquil.views.view_products', name='view_products'),
    url(_(r'^products/view/$'), 'elbroquil.views.view_products', name='view_products'),
    url(_(r'^products/confirm/$'), 'elbroquil.views.confirm_products', name='confirm_products'),
    url(_(r'^products/check/$'), 'elbroquil.views.check_products', name='check_products'),
    url(_(r'^products/upload/$'), 'elbroquil.views.upload_products', name='upload_products'),
    
    # Quarterly fee related URLs
    url(_(r'^fees/create/$'), 'elbroquil.views.create_fees', name='create_fees'),
    url(_(r'^fees/view/$'), 'elbroquil.views.view_fees', name='view_fees'),
    
    # Management related URLs
    url(_(r'^dist/view/$'), 'elbroquil.views.view_distribution_detail', name='view_distribution_detail'),
    
#    url(_(r'^email/$'), 'elbroquil.views.test_email', name='test_email'),
    
    # Admin and account URLs
    url(r'^admin/', include(admin.site.urls)),
    
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    (r'^accounts/passwordchange/$', 'django.contrib.auth.views.password_change', {'post_change_redirect': '/'}),
    (r'^accounts/passwordreset/$', 'django.contrib.auth.views.password_reset', {'post_reset_redirect': '/'}),
    (r'^accounts/passwordresetconfirm/(?P<uidb64>.+)/(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm', {'post_reset_redirect': '/'}),
        
    url(r'^rosetta/', include('rosetta.urls')),
    #(r'^i18n/', include('django.conf.urls.i18n')),
    url(_(r'^setlang/$'), 'elbroquil.views.set_language', name='set_language'),
)

