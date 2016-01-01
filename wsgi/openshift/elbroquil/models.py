from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal
from django.utils import timezone

import datetime

# Choices for "day of week" dropdowns
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

# Choices for "excel format" dropdowns
STANDARD = 0
CAL_ROSSET = 1
CAN_PIPI = 2
LA_SELVATANA = 3
CAN_PEROL = 4

EXCEL_FORMAT_CHOICES = (
    (STANDARD, _(u'Standard')),
    (CAL_ROSSET, 'Cal Rosset'),
    (CAN_PIPI, 'Can Pipirimosca'),
    (LA_SELVATANA, 'La Selvatana'),
    (CAN_PEROL, 'Can Perol'),
)

# Choices for "product status"
STATUS_NORMAL = 0
STATUS_DID_NOT_ARRIVE = 10
STATUS_MIN_ORDER_NOT_MET = 20

STATUS_CHOICES = (
    (STATUS_NORMAL, _(u'Normal')),
    (STATUS_DID_NOT_ARRIVE, _(u'Did not arrive')),
    (STATUS_MIN_ORDER_NOT_MET, _(u'Min. order not met')),
)

# Choices for "language code"

LANGUAGE_CHOICES = (
    ('tr', _(u'Turkish')),
    ('ca', _(u'Catala')),
    ('es', _(u'Castellano')),
    ('en', _(u'English')),
)

# Choices for email codes

# Member emails
EMAIL_OFFER_CREATED = 1
EMAIL_REMINDER = 2
EMAIL_ORDER_SENT_TO_PRODUCER = 3
EMAIL_ACCOUNT_CREATED = 4
EMAIL_TASK_REMINDER = 5

# Producer emails
EMAIL_PRODUCER_ORDER_TOTAL = 101
EMAIL_PRODUCER_NO_ORDER = 102
EMAIL_PRODUCER_RATINGS = 103

EMAIL_CODE_CHOICES  = (
    (EMAIL_OFFER_CREATED, _(u'Member: Offer Created')),
    (EMAIL_REMINDER, _(u'Member: Saturday Reminder')),
    (EMAIL_ORDER_SENT_TO_PRODUCER, _(u'Member: Order Sent to Producers')),
    (EMAIL_ACCOUNT_CREATED, _(u'Member: Account Created')),
    (EMAIL_TASK_REMINDER, _(u'Member: Distribution Task Reminder')),

    (EMAIL_PRODUCER_ORDER_TOTAL, _(u'Producer: Total Order')),
    (EMAIL_PRODUCER_NO_ORDER, _(u'Producer: No Order This Week')),
    (EMAIL_PRODUCER_RATINGS, _(u'Producer: Product Ratings')),
)

# Producer model
# Contains the contact information, preference for receiving orders and other information
class Producer(models.Model):
    first_name = models.CharField(_(u'first name'), max_length=50)
    last_name = models.CharField(_(u'last name'), max_length=50, null=True, blank=True)
    company_name = models.CharField(_(u'company name'), max_length=50, null=True, blank=True)
    email = models.EmailField(_(u'email'))
    send_ratings = models.BooleanField(_(u'send ratings'), default=False)
    order_day = models.SmallIntegerField(_(u'order day'), choices=DAY_OF_WEEK_CHOICES, default=MONDAY)
    order_hour = models.SmallIntegerField(_(u'order hour'), validators=[MaxValueValidator(23), MinValueValidator(0)])
    minimum_order = models.DecimalField(_(u'minimum order'), decimal_places=2, max_digits=7, null=True, blank=True)
    fixed_products = models.BooleanField(_(u'fixed products'), default=False)
    limited_availability = models.BooleanField(_(u'limited availability'), default=False)
    excel_format = models.SmallIntegerField(_(u'excel format'), choices=EXCEL_FORMAT_CHOICES, default=STANDARD)
    default_category_name = models.CharField(_(u'default category name'), max_length=50, null=True, blank=True)
    active = models.BooleanField(_(u'active'), default=True, help_text=_(u"<em>(Disable the producer by clearing this option.)</em>"))
    transportation_cost = models.DecimalField(_(u'transportation cost'), decimal_places=2, max_digits=7, default=0)

    short_product_explanation = models.CharField(_(u'short product explanation'), max_length=80, null=False, blank=False, default="", help_text=_(u"<em>(Will be shown on the 'offer created' emails.)</em>"))

    def __unicode__(self):
        return self.company_name

    class Meta:
        verbose_name = _('producer')
        verbose_name_plural = _('producers')

# Producer available date model
# For the producers with limited availability, this table contains the distribution dates
# when they are available to supply their products
class ProducerAvailableDate(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE)
    available_date = models.DateField(_(u'available date'))

    def __unicode__(self):
        return self.available_date.strftime('%d/%m/%Y')

    class Meta:
        verbose_name = _('available date')
        verbose_name_plural = _('available dates')

# Skipped distribution date model
# Contains the canceled/skipped distribution dates for which the cooperative will not make any orders
class SkippedDistributionDate(models.Model):
    skipped_date = models.DateField(_(u'skipped date'))

    def __unicode__(self):
        return self.skipped_date.strftime('%d/%m/%Y')

    class Meta:
        verbose_name = _('skipped date')
        verbose_name_plural = _('skipped dates')

# Category model
# Holds the information about product categories and contains the relation between products and producers
class Category(models.Model):
    name = models.CharField(_(u'name'), max_length=100)
    visible_name = models.CharField(_(u'visible name'), max_length=100, null=True, blank=True, help_text=_(u"<em>(To display shorter/better names for producer categories.)</em>"))
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(_(u'sort order'), default=0, blank=False, null=False, help_text=_(u"<em>(To change the order of appearance of categories.)</em>"))
    archived = models.BooleanField(_(u'archived'), default=False)

    def __unicode__(self):
        if self.visible_name and len(self.visible_name.strip()) > 0:
            return unicode(self.visible_name)
        else:
            return unicode(self.name.title())

    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')

# Product model
# Holds the product details and order summary for the product
class Product(models.Model):
    name = models.CharField(_(u'product'), max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    origin = models.CharField(_(u'origin'), max_length=100, null=True, blank=True)
    comments = models.CharField(_(u'comments'), max_length=100, null=True, blank=True)
    price = models.DecimalField(_(u'price'), decimal_places=4, max_digits=9)
    unit = models.CharField(_(u'unit'), max_length=20, help_text=_(u"<em>(without the &euro; sign or / character.)</em>"))
    integer_demand = models.BooleanField(_(u'integer demand'), default=False)
    distribution_date = models.DateField(_(u'distribution date'), null=True, blank=True, help_text=_(u"<em>(Only fill for products that are offered just once.)</em>"))
    archived = models.BooleanField(_(u'archived'), default=False)

    total_quantity = models.DecimalField(_(u'total quantity'), decimal_places=2, max_digits=7, default=0)
    arrived_quantity = models.DecimalField(_(u'arrived quantity'), decimal_places=2, max_digits=7, default=0)
    order_limit_date = models.DateTimeField(_(u'order limit date'), null=True, blank=True, help_text=_(u"<em>(Only fill for products that are offered just once.)</em>"))
    average_rating = models.DecimalField(_(u'average rating'), decimal_places=1, max_digits=5, default=0)

    new_product = models.BooleanField(_(u'new product'), default=False, help_text=_(u"<em>(To highlight this product as NEW in the order pages.)</em>"))
    sent_to_producer = models.BooleanField(_(u'sent to producer'), default=False)

    stock_product = models.BooleanField(_(u'stock product'), default=False)

    def active(self):
        return self.distribution_date >= timezone.now().date() and not self.archived

    def __unicode__(self):
        return self.name + "(" + self.category.name + "): " + self.price.__str__() + " " + self.unit

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')

# Order model
# Contains the orders made by the members. Each record holds the relation member-product-order
class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.DecimalField(_(u'quantity'), decimal_places=2, max_digits=7)
    rating = models.SmallIntegerField(_(u'rating'), null=True, blank=True, default=None)
    archived = models.BooleanField(_(u'archived'), default=False)
    status = models.SmallIntegerField(_(u'status'), choices=STATUS_CHOICES, default=STATUS_NORMAL)
    arrived_quantity = models.DecimalField(_(u'arrived quantity'), decimal_places=2, max_digits=7)

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')


# Payment-related models

# Payment model
# Holds the total payment amount made by the member
class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(_(u'date'), default=timezone.now)
    amount = models.DecimalField(_(u'quantity'), decimal_places=2, max_digits=7, default=0)

# Consumption model
# Holds the part of the payment which is due to the consumption (orders)
class Consumption(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    amount = models.DecimalField(_(u'quantity'), decimal_places=2, max_digits=7, default=0)

# Debt model
# Holds the debt of the member when the related payment is made. For each payment, the debt
# is stored to be charged for later weeks. A negative amount indicates a debt of the
# cooperative to the member
class Debt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(_(u'quantity'), decimal_places=2, max_digits=7, default=0)

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

# Quarterly fee model
# Holds the quarterly fee that is to be (or already) charged to the member
# If the payment is not null, it indicates that fee is already paid during that payment
class Quarterly(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.SmallIntegerField(_(u'year'))
    quarter = models.SmallIntegerField(_(u'quarter'))
    created_date = models.DateTimeField(_(u'created date'), default=timezone.now)
    amount = models.DecimalField(_(u'quantity'), decimal_places=2, max_digits=7, default=0)

    payment = models.ForeignKey(Payment, null=True, on_delete=models.CASCADE)

# Extra info model
# Holds the additional information for the User model
class ExtraInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    secondary_email = models.EmailField(_(u'secondary email'), blank=True, default='')
    phone = models.CharField(_(u'phone'), max_length=15)
    secondary_phone = models.CharField(_(u'secondary phone'), max_length=15, blank=True, default='')

# Distribution account detail model
# Holds the financial summary of the distribution day
class DistributionAccountDetail(models.Model):
    date = models.DateField(_(u'distribution date'), default=timezone.now)
    initial_amount = models.DecimalField(_(u'initial amount'), decimal_places=2, max_digits=7, default=0)
    member_consumed_amount = models.DecimalField(_(u'member consumed amount'), decimal_places=2, max_digits=7, default=0)
    total_member_payment_amount = models.DecimalField(_(u'total member payment amount'), decimal_places=2, max_digits=7, default=0)
    #producer_paid_amount = models.DecimalField(_(u'producer paid amount'), decimal_places=2, max_digits=7, default=0)
    debt_balance_amount= models.DecimalField(_(u'debt balance amount'), decimal_places=2, max_digits=7, default=0)
    quarterly_fee_collected_amount = models.DecimalField(_(u'collected fee amount'), decimal_places=2, max_digits=7, default=0)
    final_amount = models.DecimalField(_(u'final amount'), decimal_places=2, max_digits=7, default=0)
    expected_final_amount = models.DecimalField(_(u'expected final amount'), decimal_places=2, max_digits=7, default=0)
    notes = models.TextField(_(u'notes'), blank=True, default='')

# Producer Paymnet model
# Holds the information of a payment made to a producer
class ProducerPayment(models.Model):
    date = models.DateField(_(u'distribution date'), default=timezone.now)
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE)
    amount = models.DecimalField(_(u'quantity'), decimal_places=2, max_digits=7, default=0)

# Email Template model
# Contains editable email templates
class EmailTemplate(models.Model):
    email_code = models.SmallIntegerField(_(u'email code'), choices=EMAIL_CODE_CHOICES, default='ca')
    language = models.CharField(_(u'language code'), choices=LANGUAGE_CHOICES, default='ca', max_length=2)
    subject = models.CharField(_(u'subject'), max_length=70, blank=True, default='', help_text=_(u"<em>(Without [BroquilGotic])</em>"))
    body = models.TextField(_(u'body'), blank=True, default='', help_text=_(u"<em>(Do not remove the [[CONTENT]] parts.)</em>"))

    def full_subject(self):
        return "[BroquilGotic]" + self.subject

    def get_language_name(self):
        for code, name in LANGUAGE_CHOICES:
            if code == self.language:
                return name

        return 'Catala'

    def get_email_type(self):
        for code, email_type in EMAIL_CODE_CHOICES:
            if code == self.email_code:
                return email_type

        return ""

    def __unicode__(self):
        return unicode(self.get_email_type()) + " (" + unicode(self.get_language_name()) + ")"

    class Meta:
        verbose_name = _('email template')
        verbose_name_plural = _('email templates')

# Distribution Task model
# Contains the information for the members' obligatory distribution tasks
class DistributionTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    distribution_date = models.DateField(_(u'distribution date'))
    
# Email List model
class EmailList(models.Model):
    name = models.CharField(_(u'name'), max_length=80)
    email_addresses = models.TextField(_(u'email addresses'), blank=True, default='')
    cc_task_reminders = models.BooleanField(_(u'cc task reminders'), default=False)
    cc_incidents = models.BooleanField(_(u'cc incidents'), default=False)
    
    def __unicode__(self):
        return unicode(self.name)