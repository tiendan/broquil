from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal
from django.utils import timezone

MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

DAY_OF_WEEK_CHOICES = (
    (MONDAY, _(u'Monday')),
    (TUESDAY, _(u'Tuesday')),    
    (WEDNESDAY, _(u'Wednesday')),
    (THURSDAY, _(u'Thursday')),    
    (FRIDAY, _(u'Friday')),
    (SATURDAY, _(u'Saturday')),
    (SUNDAY, _(u'Sunday')),
)

STANDARD = 0
CAL_ROSSET = 1
CAN_PIPI = 2
LA_SELVATANA = 3

EXCEL_FORMAT_CHOICES = (  
    (STANDARD, _(u'Standard')),
    (CAL_ROSSET, 'Cal Rosset'),
    (CAN_PIPI, 'Can Pipirimosca'),    
    (LA_SELVATANA, 'La Selvatana'),  
)

STATUS_NORMAL = 0
STATUS_DID_NOT_ARRIVE = 10
STATUS_MIN_ORDER_NOT_MET = 20

STATUS_CHOICES = (  
    (STATUS_NORMAL, _(u'Normal')),
    (STATUS_DID_NOT_ARRIVE, _(u'Did not arrive')),
    (STATUS_MIN_ORDER_NOT_MET, _('Min. order not met')),
)

class Producer(models.Model):
    first_name = models.CharField(_(u'first name'), max_length=50)
    last_name = models.CharField(_(u'last name'), max_length=50, null=True, blank=True)
    company_name = models.CharField(_(u'company name'), max_length=50, null=True, blank=True)
    email = models.EmailField(_(u'email'))
    send_ratings = models.BooleanField(_(u'send ratings'), default=False)
    order_day = models.SmallIntegerField(_(u'order day'), choices=DAY_OF_WEEK_CHOICES, default=MONDAY)
    order_hour = models.SmallIntegerField(_(u'order hour'), validators=[MaxValueValidator(23), MinValueValidator(0)])
    minimum_order = models.DecimalField(_(u'minimum order'), decimal_places=2, max_digits=5, null=True, blank=True)
    fixed_products = models.BooleanField(_(u'fixed products'), default=False)
    limited_availability = models.BooleanField(_(u'limited availability'), default=False)
    excel_format = models.SmallIntegerField(_(u'excel format'), choices=EXCEL_FORMAT_CHOICES, default=STANDARD)
    default_category_name = models.CharField(_(u'default category name'), max_length=50, null=True, blank=True)
    active = models.BooleanField(_(u'active'), default=True)
    transportation_cost = models.DecimalField(_(u'transportation cost'), decimal_places=2, max_digits=5, default=0)
    
    def __unicode__(self):
        return self.first_name + " " + self.last_name + " (" + self.company_name + ")"

    class Meta:
        verbose_name = _('producer')
        verbose_name_plural = _('producers')
    
class ProducerAvailableDate(models.Model):
    producer = models.ForeignKey(Producer)
    available_date = models.DateField(_(u'available date'))
    
    def __unicode__(self):
        return self.available_date.strftime('%Y-%m-%d')

    class Meta:
        verbose_name = _('available date')
        verbose_name_plural = _('available dates')
        
class Category(models.Model):
    name = models.CharField(_(u'name'), max_length=100)
    visible_name = models.CharField(_(u'visible name'), max_length=100, null=True, blank=True)
    producer = models.ForeignKey(Producer)
    sort_order = models.PositiveIntegerField(_(u'sort order'), default=0, blank=False, null=False)
    archived = models.BooleanField(_(u'archived'), default=False)
        
    def __unicode__(self):
        if len(self.visible_name.strip()) > 0:
            return unicode(self.visible_name)
        else:
            return unicode(self.name.title())
                
    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')

class Product(models.Model):
    name = models.CharField(_(u'product'), max_length=100)
    category = models.ForeignKey(Category)
    origin = models.CharField(_(u'origin'), max_length=100, null=True, blank=True)
    comments = models.CharField(_(u'comments'), max_length=100, null=True, blank=True)
    price = models.DecimalField(_(u'price'), decimal_places=2, max_digits=5)
    unit = models.CharField(_(u'unit'), max_length=20)
    integer_demand = models.BooleanField(_(u'integer demand'), default=False)
    distribution_date = models.DateField(_(u'distribution date'), null=True, blank=True)
    archived = models.BooleanField(_(u'archived'), default=False)
    
    total_quantity = models.DecimalField(_(u'total quantity'), decimal_places=2, max_digits=5, default=0)
    arrived_quantity = models.DecimalField(_(u'arrived quantity'), decimal_places=2, max_digits=5, default=0)
    order_limit_date = models.DateField(_(u'order limit date'), null=True, blank=True)
    average_rating = models.DecimalField(_(u'average rating'), decimal_places=1, max_digits=5, default=0)
    
    def active(self):
        return self.distribution_date >= timezone.now().date() and not self.archived 
        
    def __unicode__(self):
        return self.name + "(" + self.category.name + "): " + self.price.__str__() + " " + self.unit

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
    
class Order(models.Model):
    product = models.ForeignKey(Product)
    user = models.ForeignKey(User)
    quantity = models.DecimalField(_(u'quantity'), decimal_places=2, max_digits=5)
    rating = models.SmallIntegerField(_(u'rating'), null=True, blank=True, default=None)
    arrived = models.BooleanField(_(u'arrived'), default=True)
    canceled = models.BooleanField(_(u'canceled'), default=False)
    archived = models.BooleanField(_(u'archived'), default=False)
    status = models.SmallIntegerField(_(u'status'), choices=STATUS_CHOICES, default=STATUS_NORMAL)
    arrived_quantity = models.DecimalField(_(u'arrived quantity'), decimal_places=2, max_digits=5)

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')