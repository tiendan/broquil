from django.contrib import admin
import elbroquil.models as models
from django.utils.translation import ugettext as _

# Register your models here.
class AvailabilityInline(admin.TabularInline):
    model = models.ProducerAvailableDate
    extra = 2
    
    verbose_name_plural = _(u"Producer availability (in case of limited availability)")
    verbose_name = _(u"date")
    
    
class ProducerAdmin(admin.ModelAdmin):
    fieldsets = [
      (_(u'General Info'), {'fields': ['first_name', 'last_name', 'company_name', 'email']}),
      (_(u'Order Info'), {'fields': ['send_ratings', 'order_day', 'order_hour', 'minimum_order', 'fixed_products', 'limited_availability']}),
      (_(u'Technical Info'), {'fields': ['excel_format', 'default_category_name', 'active']}),
    ]
    inlines = [AvailabilityInline]
    list_display = ('first_name', 'last_name', 'company_name', 'email', 'active')

class CategoryAdmin(admin.ModelAdmin):
    verbose_name_plural = _(u"Categories")
    list_display = ('sort_order', 'name', 'producer')
    
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'unit')

admin.site.register(models.Producer, ProducerAdmin)

admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Product) #, ProductAdmin)