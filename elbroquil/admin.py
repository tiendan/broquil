import logging

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.utils.translation import ugettext as _

import elbroquil.libraries as libs
import elbroquil.models as models

from suit_redactor.widgets import RedactorWidget

# Get an instance of a logger
logger = logging.getLogger("MYAPP")


# Producer availability model is shown inline in the producer admin pages
class AvailabilityInline(admin.TabularInline):
    model = models.ProducerAvailableDate
    extra = 2

    verbose_name_plural = _(
        "Producer availability (in case of limited availability)")
    verbose_name = _("date")


class ProducerForm(forms.ModelForm):
    class Meta:
        widgets = {
            'description': RedactorWidget(editor_options={'lang': 'ca'})
        }


# Producer admin pages
class ProducerAdmin(admin.ModelAdmin):
    form = ProducerForm
    fieldsets = (
        (_('General Info'), {'fields': [
         'first_name', 'last_name', 'company_name', 'email', 'description']}),
        (_('Order Info'), {'fields': ['order_day',
                                       'order_hour',
                                       'minimum_order',
                                       'transportation_cost',
                                       'fixed_products',
                                       'limited_availability']}),
        (_('Technical Info'), {'fields': [
            'short_product_explanation', 'excel_format', 'active']}),
    )
    inlines = [AvailabilityInline]
    list_display = ('company_name', 'email', 'active')


# Category admin pages
class CategoryAdmin(admin.ModelAdmin):
    verbose_name_plural = _("Categories")
    list_display = ('sort_order', 'name', 'producer')
    list_display_links = ('name',)
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'visible_name', 'producer', 'sort_order')}
         ),
    )

    # Override default queryset so that only relevant products are shown
    def get_queryset(self, request):
        qs = super(CategoryAdmin, self).get_queryset(
            request).order_by('sort_order', 'pk')

        return qs


# Product admin pages
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'unit', 'distribution_date')
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'category', 'origin', 'comments', 'price',
                       'unit', 'integer_demand', 'stock_product',
                       'new_product', 'distribution_date', 'order_limit_date')}
         ),
    )

    # Override default queryset so that only relevant products are shown
    def get_queryset(self, request):
        qs = super(ProductAdmin, self).get_queryset(request).filter(
            Q(distribution_date__gte=libs.get_today()) |
            Q(distribution_date=None)) \
            .order_by('category__sort_order', 'pk')

        return qs


# User definition/update pages
# We define extra information as inline form component, then customize
# the user forms and re-register the new user admin


# Define an inline admin descriptor for ExtraInfo model
# which acts a bit like a singleton
class ExtraInfoInline(admin.StackedInline):
    model = models.ExtraInfo
    can_delete = False
    verbose_name_plural = 'extra info'


class CustomUserCreationForm(UserCreationForm):
    username = forms.RegexField(
        label=_("Email"),
        max_length=75,
        regex=r'^[\w.@+-]+$',
        help_text=_(
            """Required. 30 characters or fewer. """
            """Letters, digits and @/./+/-/_ only."""),
        error_messages={'invalid': _(
            """This value may contain only letters, """
            """numbers and @/./+/-/_ characters.""")})

    first_name = forms.CharField(label=_("First name"))
    last_name = forms.CharField(label=_("Last name"))

    phone = forms.RegexField(
        label=_("Phone number"),
        max_length=15,
        regex=r'^[0-9]+$',
        help_text=_('This will be the initial password for the member.') +
        ' ' +
        _('Numbers only.'),)

    secondary_email = forms.EmailField(
        label=_("Alternative email"), required=False)
    secondary_phone = forms.CharField(
        label=_("Alt. phone number"), max_length=15, required=False)

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        # If one field gets autocompleted but not the other, our 'neither
        # password or both password' validation will be triggered.
        self.fields['password1'].widget.attrs['autocomplete'] = 'off'
        self.fields['password2'].widget.attrs['autocomplete'] = 'off'

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name"]

    def clean_username(self):
        # cleaned_data = super(UserCreationForm, self).clean()

        username = self.cleaned_data["username"]
        try:
            User.objects.get(username=username)
            raise forms.ValidationError(
                _("A user with that username already exists."))
        except User.DoesNotExist:
            return username

    def clean_password(self):
        return ""

    def clean_password2(self):
        return ""

    def save(self, commit=True):
        user = super(CustomUserCreationForm, self).save(commit=True)

        user.set_password(self.cleaned_data["phone"])
        user.email = self.cleaned_data["username"]

        logger.error("User saved")
        user.save()

        extra = models.ExtraInfo(
            user=user,
            phone=self.cleaned_data["phone"],
            secondary_email=self.cleaned_data["secondary_email"],
            secondary_phone=self.cleaned_data["secondary_phone"])
        extra.save()

        # Send welcome email to the user
        email_subject = '[BroquilGotic]Benvingut al Broquil!'
        html_content = """<p style="text-align: center;"><strong>
            <u>El Br&ograve;quil Del G&ograve;tic</u></strong></p>
            <p style="text-align: left;">Hola broquilire!!!!</p>
            <p style="text-align: left;">A partir d\'ara ja pots fer la teva
            comanda, per a aprendre com fer la comanda, pots mirar la ajuda en
            <a href="http://el-broquil.rhcloud.com">la pagina web</a></p>
            <p>Salut!! amb el broquil :P</p>"""

        # If there is an email template stored in DB, use it
        email = models.EmailTemplate.objects.filter(
            email_code=models.EMAIL_ACCOUNT_CREATED).first()

        if email:
            email_subject = email.full_subject()
            html_content = email.body

        libs.send_email_to_user(email_subject, html_content, user)

        logger.error("... and saved")

        return user


# Define a new User admin
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name',
                       'phone', 'secondary_email', 'secondary_phone')}
         ),
    )
    inlines = ()

    def add_view(self, request):
        self.inlines = ()
        return super(CustomUserAdmin, self).add_view(request)

    def change_view(self, request, object_id):
        self.inlines = (ExtraInfoInline, )
        return super(CustomUserAdmin, self).change_view(request, object_id)


class CustomUserAdminActiveUsers(CustomUserAdmin):
    # Override default queryset so that only relevant users are shown
    def get_queryset(self, request):
        qs = super(CustomUserAdminActiveUsers, self) \
            .get_queryset(request) \
            .filter(Q(is_active=True) &
                    Q(username__contains='@')) \
            .order_by('first_name', 'last_name')

        return qs


class CustomUserAdminInactiveUsers(CustomUserAdmin):
    # Override default queryset so that only relevant users are shown
    def get_queryset(self, request):
        qs = super(CustomUserAdminInactiveUsers, self) \
            .get_queryset(request) \
            .filter(~Q(is_active=True) &
                    Q(username__contains='@')) \
            .order_by('first_name', 'last_name')

        return qs


class CustomUserAdminSystemUsers(CustomUserAdmin):
    # Override default queryset so that only relevant users are shown
    def get_queryset(self, request):
        qs = super(CustomUserAdminSystemUsers, self) \
            .get_queryset(request) \
            .filter(~Q(username__contains='@')) \
            .order_by('username')

        return qs


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        widgets = {
            'body': RedactorWidget(editor_options={'lang': 'ca'})
        }


class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateForm
    fieldsets = (
        (_('Information'), {'classes': ('full-width',),
                             'fields': ('email_code', 'language',)}),
        (_('Email'), {'classes': ('full-width',),
                       'fields': ('subject', 'body',)}),
    )
    ordering = ['email_code', 'language']


class EmailListAdmin(admin.ModelAdmin):
    verbose_name_plural = _("Email Lists")
    list_display = ('name',)
    list_display_links = ('name',)
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'description', 'email_addresses',
                       'cc_task_reminders', 'cc_incidents')}
         ),
    )


class AccountMovementAdmin(admin.ModelAdmin):
    list_display = ('movement_date', 'amount', 'explanation')
    list_display_links = ('movement_date',)
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('movement_type', 'amount', 'final_amount',
                       'explanation', 'movement_date')}
         ),
    )
    ordering = ['-movement_date']


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdminActiveUsers)


class InactiveUser(User):
    class Meta:
        proxy = True
        app_label = "auth"
        verbose_name = _('user (inactive)')
        verbose_name_plural = _('users (inactive)')


class SystemUser(User):
    class Meta:
        proxy = True
        app_label = "auth"
        verbose_name = _('user (system)')
        verbose_name_plural = _('users (system)')

admin.site.register(InactiveUser, CustomUserAdminInactiveUsers)
admin.site.register(SystemUser, CustomUserAdminSystemUsers)

admin.site.register(Permission)


admin.site.register(models.Producer, ProducerAdmin)

admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Product, ProductAdmin)
admin.site.register(models.SkippedDistributionDate)
admin.site.register(models.EmailTemplate, EmailTemplateAdmin)
admin.site.register(models.EmailList, EmailListAdmin)
admin.site.register(models.AccountMovement, AccountMovementAdmin)
