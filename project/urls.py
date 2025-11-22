import elbroquil.views as broquil_views
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from elbroquil.views.fee_views import CreateFeesView, ViewFeesView
from elbroquil.views.management_views import (
    ViewAccountingDetailView,
    ViewDebtsView,
    ViewDistributionDetailView,
    ViewDistributionTaskInformationView,
)
from elbroquil.views.order_views import OrderHistoryView, UpdateOrderView, ViewOrderView
from elbroquil.views.other_views import ContactView, ProducerInfoView, SetLanguageView, TasksView
from elbroquil.views.product_views import CheckProductsView, ConfirmProductsView, UploadProductsView, ViewProductsView

urlpatterns = [
    re_path(r"^$", ViewOrderView.as_view(), name="site_root"),
    re_path(_(r"^help/"), TemplateView.as_view(template_name="help.html"), name="help"),
    re_path(r"^health/", TemplateView.as_view(template_name="help.html"), name="health"),
    re_path(_(r"^contact/$"), ContactView.as_view(), name="contact"),
    re_path(_(r"^tasks/$"), TasksView.as_view(), name="tasks"),
    # Distribution related URLs
    re_path(_(r"^dist/$"), broquil_views.view_order_totals, name="view_order_totals"),
    re_path(_(r"^dist/cash/$"), broquil_views.count_initial_cash, name="count_initial_cash"),
    re_path(_(r"^dist/baskets/$"), broquil_views.view_basket_counts, name="view_basket_counts"),
    re_path(_(r"^dist/([0-9]+)/$"), broquil_views.view_product_orders, name="view_product_orders"),
    re_path(
        _(r"^dist/product/([0-9]+)/$"), broquil_views.view_product_orders_with_id, name="view_product_orders_with_id"
    ),
    re_path(_(r"^dist/payment/$"), broquil_views.member_payment, name="member_payment"),
    re_path(_(r"^dist/account/$"), broquil_views.account_summary, name="account_summary"),
    # Order related URLs
    re_path(_(r"^order/([0-9]+)/$"), UpdateOrderView.as_view(), name="update_order"),
    re_path(_(r"^order/history$"), OrderHistoryView.as_view(), name="order_history"),
    re_path(_(r"^order/$"), ViewOrderView.as_view(), name="view_order"),
    # Product related URLs
    re_path(_(r"^products/view/(?P<producer_id>[0-9]+)$"), ViewProductsView.as_view(), name="view_products"),
    re_path(_(r"^products/view/$"), ViewProductsView.as_view(), name="view_products"),
    re_path(_(r"^products/confirm/$"), ConfirmProductsView.as_view(), name="confirm_products"),
    re_path(_(r"^products/check/$"), CheckProductsView.as_view(), name="check_products"),
    re_path(_(r"^products/upload/$"), UploadProductsView.as_view(), name="upload_products"),
    re_path(_(r"^producer/$"), ProducerInfoView.as_view(), name="producer_info"),
    re_path(_(r"^producer/(?P<producer_id>[0-9]+)$"), ProducerInfoView.as_view(), name="producer_info"),
    # Quarterly fee related URLs
    re_path(_(r"^fees/create/$"), CreateFeesView.as_view(), name="create_fees"),
    re_path(_(r"^fees/view/$"), ViewFeesView.as_view(), name="view_fees"),
    # Management related URLs
    re_path(_(r"^man/account/$"), ViewAccountingDetailView.as_view(), name="view_accounting_detail"),
    re_path(_(r"^man/dist/$"), ViewDistributionDetailView.as_view(), name="view_distribution_detail"),
    re_path(_(r"^man/debts/$"), ViewDebtsView.as_view(), name="view_debts"),
    re_path(
        _(r"^man/perm/$"), ViewDistributionTaskInformationView.as_view(), name="view_distribution_task_information"
    ),
    # Admin and account URLs
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^accounts/login/$", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    re_path(r"^accounts/logout/$", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    re_path(
        r"^accounts/passwordchange/$", auth_views.PasswordChangeView.as_view(success_url="/"), name="password_change"
    ),
    re_path(
        r"^accounts/passwordreset/$", auth_views.PasswordResetView.as_view(success_url="/"), name="password_reset"
    ),
    re_path(
        r"^accounts/passwordresetconfirm/(?P<uidb64>.+)/(?P<token>.+)/$",
        auth_views.PasswordResetConfirmView.as_view(success_url="/"),
        name="password_reset_confirm",
    ),
    re_path(r"^rosetta/", include("rosetta.urls")),
    # (r'^i18n/', include('django.conf.urls.i18n')),
    re_path(_(r"^setlang/$"), SetLanguageView.as_view(), name="set_language"),
    re_path(r"^ckeditor5/", include("django_ckeditor_5.urls")),
]
