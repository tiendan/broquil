from django import forms
from django.contrib.admin import widgets as admin_widgets
#from django.contrib.auth.models import User
import elbroquil.models as models
from django.utils.translation import ugettext_lazy as _


class UploadProductsForm(forms.Form):
    producer = forms.ModelChoiceField(queryset=models.Producer.objects.all(),
                                           label=_('Producer'))
    excel_file = forms.FileField()
    
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

class UpdateOrderForm(forms.Form):
    def __init__(self, product_list, *args, **kwargs):
        super(UpdateOrderForm, self).__init__(*args, **kwargs)
        
        for prods in product_list:
            for prod in prods:
                self.fields['product_%i' % prod.id] = forms.DecimalField()

