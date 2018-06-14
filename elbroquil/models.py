from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

# Choices for "day of week" dropdowns
MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

DAY_OF_WEEK_CHOICES = (
    (MONDAY, _('Monday')),
    (TUESDAY, _('Tuesday')),
    (WEDNESDAY, _('Wednesday')),
    (THURSDAY, _('Thursday')),
    (FRIDAY, _('Friday')),
    (SATURDAY, _('Saturday')),
    (SUNDAY, _('Sunday')),
)

# Choices for "excel format" dropdowns
STANDARD = 0
CAL_ROSSET = 1
CAN_PIPI = 2
LA_SELVATANA = 3
CAN_PEROL = 4

EXCEL_FORMAT_CHOICES = (
    (STANDARD, _('Standard')),
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
    (STATUS_NORMAL, _('Normal')),
    (STATUS_DID_NOT_ARRIVE, _('Did not arrive')),
    (STATUS_MIN_ORDER_NOT_MET, _('Min. order not met')),
)

# Choices for "language code"

LANGUAGE_CHOICES = (
    ('tr', _('Turkish')),
    ('ca', _('Catala')),
    ('es', _('Castellano')),
    ('en', _('English')),
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

EMAIL_CODE_CHOICES = (
    (EMAIL_OFFER_CREATED, _('Member: Offer Created')),
    (EMAIL_REMINDER, _('Member: Saturday Reminder')),
    (EMAIL_ORDER_SENT_TO_PRODUCER, _('Member: Order Sent to Producers')),
    (EMAIL_ACCOUNT_CREATED, _('Member: Account Created')),
    (EMAIL_TASK_REMINDER, _('Member: Distribution Task Reminder')),

    (EMAIL_PRODUCER_ORDER_TOTAL, _('Producer: Total Order')),
    (EMAIL_PRODUCER_NO_ORDER, _('Producer: No Order This Week')),
    (EMAIL_PRODUCER_RATINGS, _('Producer: Product Ratings')),
)

# Account movements
MOVEMENT_FROM_SAFE = 1
MOVEMENT_TO_SAFE = 2

MOVEMENT_CHOICES = (
    (MOVEMENT_FROM_SAFE, _('Transfer from SAFE to DRAWER')),
    (MOVEMENT_TO_SAFE, _('Transfer from DRAWER to SAFE')),
)


# Producer model
# Contains the contact information, preference for receiving orders and
# other information
class Producer(models.Model):
    first_name = models.CharField(_('first name'), max_length=50)
    last_name = models.CharField(
        _('last name'), max_length=50, null=True, blank=True)
    company_name = models.CharField(
        _('company name'), max_length=50, null=True, blank=True)
    email = models.EmailField(_('email'))
    send_ratings = models.BooleanField(_('send ratings'), default=False)
    order_day = models.SmallIntegerField(
        _('order day'), choices=DAY_OF_WEEK_CHOICES, default=MONDAY)
    order_hour = models.SmallIntegerField(
        _('order hour'),
        validators=[MaxValueValidator(23), MinValueValidator(0)])
    minimum_order = models.DecimalField(
        _('minimum order'),
        decimal_places=2,
        max_digits=7,
        null=True,
        blank=True)
    fixed_products = models.BooleanField(_('fixed products'), default=False)
    limited_availability = models.BooleanField(
        _('limited availability'), default=False)
    excel_format = models.SmallIntegerField(
        _('excel format'), choices=EXCEL_FORMAT_CHOICES, default=STANDARD)
    default_category_name = models.CharField(
        _('default category name'), max_length=50, null=True, blank=True)
    active = models.BooleanField(_('active'), default=True, help_text=_(
        "<em>(Disable the producer by clearing this option.)</em>"))
    transportation_cost = models.DecimalField(
        _('transportation cost'), decimal_places=2, max_digits=7, default=0)

    short_product_explanation = models.CharField(
        _('short product explanation'), max_length=80, null=False,
        blank=False, default="",
        help_text=_("<em>(Will be shown on the 'offer created' emails.)</em>"))
    description = models.TextField(
        _('description'), blank=True, default='',
        help_text=_("<em>(Long explanation about the producer. If you want to place photos or links to files, a) place them in Google Drive and create public link, b) find their public link from some other website)</em>"))

    def __unicode__(self):
        return self.company_name

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = _('producer')
        verbose_name_plural = _('producers')


# Producer available date model
# For the producers with limited availability, this table contains the
# distribution dates when they are available to supply their products
class ProducerAvailableDate(models.Model):
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE)
    available_date = models.DateField(_('available date'))

    def __unicode__(self):
        return self.available_date.strftime('%d/%m/%Y')

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = _('available date')
        verbose_name_plural = _('available dates')


# Skipped distribution date model
# Contains the canceled/skipped distribution dates for which the
# cooperative will not make any orders
class SkippedDistributionDate(models.Model):
    skipped_date = models.DateField(_('skipped date'))

    def __unicode__(self):
        return self.skipped_date.strftime('%d/%m/%Y')

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = _('skipped date')
        verbose_name_plural = _('skipped dates')


# Category model
# Holds the information about product categories and contains the relation
# between products and producers
class Category(models.Model):
    name = models.CharField(_('name'), max_length=100)
    visible_name = models.CharField(
        _('visible name'), max_length=100, null=True, blank=True,
        help_text=_("<em>(To display shorter/better names for producer categories.)</em>"))
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(
        _('sort order'), default=0, blank=False, null=False,
        help_text=_("<em>(To change the order of appearance of categories.)</em>"))
    archived = models.BooleanField(_('archived'), default=False)

    def __unicode__(self):
        if self.visible_name and len(self.visible_name.strip()) > 0:
            return str(self.visible_name)
        else:
            return str(self.name.title())

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')

# Product model
# Holds the product details and order summary for the product


class Product(models.Model):
    name = models.CharField(_('product'), max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    origin = models.CharField(
        _('origin'), max_length=100, null=True, blank=True)
    comments = models.CharField(
        _('comments'), max_length=100, null=True, blank=True)
    price = models.DecimalField(_('price'), decimal_places=4, max_digits=9)
    unit = models.CharField(_('unit'), max_length=20, help_text=_(
        "<em>(without the &euro; sign or / character.)</em>"))
    integer_demand = models.BooleanField(_('integer demand'), default=False)
    distribution_date = models.DateField(
        _('distribution date'), null=True, blank=True,
        help_text=_("<em>(Only fill for products that are offered just once.)</em>"))
    archived = models.BooleanField(_('archived'), default=False)

    total_quantity = models.DecimalField(
        _('total quantity'), decimal_places=2, max_digits=7, default=0)
    arrived_quantity = models.DecimalField(
        _('arrived quantity'), decimal_places=2, max_digits=7, default=0)
    order_limit_date = models.DateTimeField(
        _('order limit date'), null=True, blank=True,
        help_text=_("<em>(Only fill for products that are offered just once.)</em>"))
    average_rating = models.DecimalField(
        _('average rating'), decimal_places=1, max_digits=5, default=0)

    new_product = models.BooleanField(
        _('new product'), default=False,
        help_text=_("<em>(To highlight this product as NEW in the order pages.)</em>"))
    sent_to_producer = models.BooleanField(
        _('sent to producer'), default=False)

    stock_product = models.BooleanField(_('stock product'), default=False)

    def active(self):
        return self.distribution_date >= timezone.now().date() and \
            not self.archived

    def __unicode__(self):
        return self.name + "(" + self.category.name + "): " \
            + self.price.__str__() + " " + self.unit

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')


# Order model
# Contains the orders made by the members. Each record holds the relation
# member-product-order
class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.DecimalField(
        _('quantity'), decimal_places=2, max_digits=7)
    rating = models.SmallIntegerField(
        _('rating'), null=True, blank=True, default=None)
    archived = models.BooleanField(_('archived'), default=False)
    status = models.SmallIntegerField(
        _('status'), choices=STATUS_CHOICES, default=STATUS_NORMAL)
    arrived_quantity = models.DecimalField(
        _('arrived quantity'), decimal_places=2, max_digits=7)

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')


# Payment-related models

# Payment model
# Holds the total payment amount made by the member
class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(_('date'), default=timezone.now)
    amount = models.DecimalField(
        _('quantity'), decimal_places=2, max_digits=7, default=0)


# Consumption model
# Holds the part of the payment which is due to the consumption (orders)
class Consumption(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    amount = models.DecimalField(
        _('quantity'), decimal_places=2, max_digits=7, default=0)


# Debt model
# Holds the debt of the member when the related payment is made.
# For each payment, the debt is stored to be charged for later weeks.
# A negative amount indicates a debt of the cooperative to the member
class Debt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(
        _('quantity'), decimal_places=2, max_digits=7, default=0)

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)


# Quarterly fee model
# Holds the quarterly fee that is to be (or already) charged to the member
# If the payment is not null, it indicates that fee is already paid during
# that payment
class Quarterly(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.SmallIntegerField(_('year'))
    quarter = models.SmallIntegerField(_('quarter'))
    created_date = models.DateTimeField(
        _('created date'), default=timezone.now)
    amount = models.DecimalField(
        _('quantity'), decimal_places=2, max_digits=7, default=0)

    payment = models.ForeignKey(Payment, null=True, on_delete=models.CASCADE)


# Extra info model
# Holds the additional information for the User model
class ExtraInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    secondary_email = models.EmailField(
        _('secondary email'), blank=True, default='')
    phone = models.CharField(_('phone'), max_length=15)
    secondary_phone = models.CharField(
        _('secondary phone'), max_length=15, blank=True, default='')


# Distribution account detail model
# Holds the financial summary of the distribution day
class DistributionAccountDetail(models.Model):
    date = models.DateField(_('distribution date'), default=timezone.now)
    initial_amount = models.DecimalField(
        _('initial amount'), decimal_places=2, max_digits=7, default=0)
    member_consumed_amount = models.DecimalField(
        _('member consumed amount'), decimal_places=2,
        max_digits=7, default=0)
    total_member_payment_amount = models.DecimalField(
        _('total member payment amount'), decimal_places=2,
        max_digits=7, default=0)

    debt_balance_amount = models.DecimalField(
        _('debt balance amount'), decimal_places=2, max_digits=7, default=0)
    quarterly_fee_collected_amount = models.DecimalField(
        _('collected fee amount'), decimal_places=2, max_digits=7, default=0)
    final_amount = models.DecimalField(
        _('final amount'), decimal_places=2, max_digits=7, default=0)
    expected_final_amount = models.DecimalField(
        _('expected final amount'), decimal_places=2, max_digits=7, default=0)
    notes = models.TextField(_('notes'), blank=True, default='')


# Producer Paymnet model
# Holds the information of a payment made to a producer
class ProducerPayment(models.Model):
    date = models.DateField(_('distribution date'), default=timezone.now)
    producer = models.ForeignKey(Producer, on_delete=models.CASCADE)
    amount = models.DecimalField(
        _('quantity'), decimal_places=2, max_digits=7, default=0)


# Email Template model
# Contains editable email templates
class EmailTemplate(models.Model):
    email_code = models.SmallIntegerField(
        _('email code'), choices=EMAIL_CODE_CHOICES, default='ca')
    language = models.CharField(
        _('language code'), choices=LANGUAGE_CHOICES,
        default='ca', max_length=2)
    subject = models.CharField(
        _('subject'), max_length=70, blank=True, default='',
        help_text=_("<em>(Without [BroquilGotic])</em>"))
    body = models.TextField(
        _('body'), blank=True, default='',
        help_text=_("<em>(Do not remove the [[CONTENT]] parts.)</em>"))

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
        return str(self.get_email_type()) \
            + " (" + str(self.get_language_name()) + ")"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = _('email template')
        verbose_name_plural = _('email templates')


# Distribution Task model
# Contains the information for the members' obligatory distribution tasks
class DistributionTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    distribution_date = models.DateField(_('distribution date'))


# Email List model
# Holds information about email lists in the system (for use in the
# contact form)
class EmailList(models.Model):
    name = models.CharField(_('name'), max_length=80)
    description = models.TextField(_('description'), blank=True, default='')
    email_addresses = models.TextField(
        _('email addresses'), blank=True, default='')
    cc_task_reminders = models.BooleanField(
        _('cc task reminders'), default=False)
    cc_incidents = models.BooleanField(_('cc incidents'), default=False)

    def __unicode__(self):
        return str(self.name)

    def __str__(self):
        return self.__unicode__()


# Account Movement model
# Contains the movements between the safe box and the daily-use money drawer
class AccountMovement(models.Model):
    movement_type = models.SmallIntegerField(
        _('movement type'), choices=MOVEMENT_CHOICES,
        default=MOVEMENT_FROM_SAFE)
    amount = models.DecimalField(
        _('amount'), decimal_places=2, max_digits=7, default=0)
    final_amount = models.DecimalField(
        _('final amount in safe'), decimal_places=2, max_digits=7, default=0)
    explanation = models.TextField(_('explanation'), blank=True, default='')
    movement_date = models.DateTimeField(
        _('movement date'), default=timezone.now)
