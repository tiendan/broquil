from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django import forms
from django.contrib.auth.forms import UserCreationForm
import elbroquil.models as models
from django.utils.translation import ugettext as _
from suit_redactor.widgets import RedactorWidget
from django.contrib.auth.models import Permission


from django.db.models import Q
import elbroquil.libraries as libs

# Producer availability model is shown inline in the producer admin pages
class AvailabilityInline(admin.TabularInline):
    model = models.ProducerAvailableDate
    extra = 2
    
    verbose_name_plural = _(u"Producer availability (in case of limited availability)")
    verbose_name = _(u"date")
    
# Producer admin pages
class ProducerAdmin(admin.ModelAdmin):
    fieldsets = [
      (_(u'General Info'), {'fields': ['first_name', 'last_name', 'company_name', 'email']}),
      (_(u'Order Info'), {'fields': ['order_day', 'order_hour', 'minimum_order', 'transportation_cost', 'fixed_products', 'limited_availability']}),
      (_(u'Technical Info'), {'fields': ['short_product_explanation', 'excel_format', 'active']}),
    ]
    inlines = [AvailabilityInline]
    list_display = ('company_name', 'email', 'active')

# Category admin pages
class CategoryAdmin(admin.ModelAdmin):
    verbose_name_plural = _(u"Categories")
    list_display = ('sort_order', 'name', 'producer')
    list_display_links = ('name',)
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'visible_name', 'producer', 'sort_order')}
        ),
    )

    # Override default queryset so that only relevant products are shown
    def queryset(self, request):
        qs = super(CategoryAdmin, self).queryset(request).order_by('sort_order', 'pk')

        return qs

# Product admin pages
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'unit', 'distribution_date')
    fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'category', 'origin', 'comments', 'price', 'unit', 'integer_demand', 'new_product', 'distribution_date', 'order_limit_date')}
        ),
    )

    # Override default queryset so that only relevant products are shown
    def queryset(self, request):
        qs = super(ProductAdmin, self).queryset(request).filter(Q(distribution_date__gt=libs.get_today()) | Q(distribution_date=None)).order_by('category__sort_order', 'pk')
        
        return qs

# User definition/update pages
# We define extra information as inline form component, then customize the user forms 
# and re-register the new user admin

# Define an inline admin descriptor for ExtraInfo model
# which acts a bit like a singleton
class ExtraInfoInline(admin.StackedInline):
    model = models.ExtraInfo
    can_delete = False
    verbose_name_plural = 'extra info'

class CustomUserCreationForm(UserCreationForm):
    username = forms.RegexField(label=_("Email"), max_length=30, regex=r'^[\w.@+-]+$',
        help_text = _("Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only."),
        error_messages = {'invalid': _("This value may contain only letters, numbers and @/./+/-/_ characters.")})
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), widget=forms.PasswordInput,
        help_text = _("Enter the same password as above, for verification."))
    #email = forms.EmailField(label = _(u"Email"))
    first_name = forms.CharField(label = _(u"First name"))
    last_name = forms.CharField(label = _(u"Last name"))
    
    #phone = forms.CharField(label = _(u"Phone number"))
    #secondary_email = forms.EmailField(label = _(u"Alternative email"))
    #secondary_phone = forms.CharField(label = _(u"Alt. phone number"))
    
    class Meta:
        model = User
        fields = ("username",)
        
    def clean_username(self):
        username = self.cleaned_data["username"]
        
        # First validate that phone number exists (was not easy to do it elsewhere)
        phone_number = self.data.get("extrainfo-0-phone", "")
        if phone_number == "":
            raise forms.ValidationError(_("Phone number is required."))
        
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(_("A user with that username already exists."))

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.data["extrainfo-0-phone"])
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["username"]
        #user.extrainfo.email = self.cleaned_data["secondary_email"]
        if commit:
            user.save()
        return user
                
class CustomUserCreationForm2(UserCreationForm):
    username = forms.RegexField(label=_("Email"), max_length=30, regex=r'^[\w.@+-]+$',
        help_text = _("Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only."),
        error_messages = {'invalid': _("This value may contain only letters, numbers and @/./+/-/_ characters.")})
    first_name = forms.CharField(label = _(u"First name"))
    last_name = forms.CharField(label = _(u"Last name"))
    phone = forms.CharField(label = _(u"Phone"), max_length=15)
    secondary_email = forms.EmailField(label = _(u"Secondary email"), required=False)
    secondary_phone = forms.CharField(label = _(u"Secondary phone"), max_length=15, required=False)

    class Meta:
        model = User
        fields = ("username",)

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(_("A user with that username already exists."))
    
    def save(self, commit=True):
        #user = User()
        #raise Exception("Something's wrong.")
        
        user = super(UserCreationForm, self).save(commit=False)
        
        
        #user.username = self.cleaned_data["username"]
        user.set_password(self.cleaned_data["phone"])
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["username"]
        
        #user.extrainfo.email = self.cleaned_data["secondary_email"]
        if commit:
            user.save()
            
            
            # Create the record for extra user information
            extrainfo = models.ExtraInfo()
            extrainfo.user = user
            extrainfo.secondary_email = self.cleaned_data["secondary_email"]
            extrainfo.phone = self.cleaned_data["phone"]
            extrainfo.secondary_phone = self.cleaned_data["secondary_phone"]
            extrainfo.save()
        
        return user
          
# Define a new User admin
class UserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'password1', 'password2')} #, 'phone', 'secondary_email', 'secondary_phone')}
        ),
    )
    inlines = (ExtraInfoInline, )

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        widgets = {
            'body': RedactorWidget(editor_options={'lang': 'ca'})
        }

class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateForm
    fieldsets = [
      (_(u'Information'), {'classes': ('full-width',), 'fields': ('email_code','language',)}),
      (_(u'Email'), {'classes': ('full-width',), 'fields': ('subject', 'body',)}),
    ]

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Permission)

admin.site.register(models.Producer, ProducerAdmin)

admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Product, ProductAdmin)
admin.site.register(models.SkippedDistributionDate)
admin.site.register(models.EmailTemplate, EmailTemplateAdmin)