from django import forms
from django.contrib.admin import widgets as admin_widgets
import elbroquil.models as models
from django.utils.translation import ugettext_lazy as _


class UploadProductsForm(forms.Form):
    producer = forms.ModelChoiceField(queryset=models.Producer.objects.all(),
                                           label=_('Producer'))
    excel_file = forms.FileField(label=_('Excel file'))
    
    def __unicode__(self):
            from formadmin.forms import as_django_admin
            return as_django_admin(self)

    fieldsets = (
        ('Upload file', {
            'fields': ('producer', 'excel_file')
        }),
    )


class CheckProductsForm(forms.Form):
    table_data = forms.CharField()
    producer_id = forms.IntegerField()
    distribution_date = forms.CharField()
    order_limit_date = forms.CharField()

#class ContactForm(forms.Form):
#    