from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum

import email
import imaplib
import os
import project.settings as settings
import xlrd

from django.db import transaction
from django.utils import timezone

import elbroquil.libraries as libs
import elbroquil.models as models
import elbroquil.parse as parser


def send_order_to_producers():
    print('Comprobando si hay pedidos para enviar a los productores...')

    # Select active producers
    producers = models.Producer.objects.filter(active=True)

    # Were there any orders that were processed in this run?
    some_orders_processed = False

    next_dist_date = libs.get_next_distribution_date()

    # For each producer defined in the system
    for producer in producers:
        # Get the products which have exceeded their order limit dates
        # and which are not yet sent to the producer
        products = models.Product.objects.filter(
            order_limit_date__lt=libs.get_now(),
            sent_to_producer=False,
            category__producer=producer) \
            .order_by('category__sort_order', 'id')

        # If there are no products, continue
        if len(products) == 0:
            print('No hay productos para este productor.')
            continue

        print('Productor: %s...' % producer.company_name)
        print('%d productos pendientes de enviar al productor...' % len(products))

        # If these products belong to the next distribution date
        # Mark this variable so that later on we may decide to send emails
        # to cooperative members informing that their orders were sent
        if products[0].distribution_date == next_dist_date:
            some_orders_processed = True

        order_total = 0

        # Calculate total ordered quantity for each product
        for product in products:
            total_quantity = models.Order.objects \
                                 .filter(product=product) \
                                 .aggregate(Sum('quantity'))['quantity__sum'] or Decimal(0)
            product.total_quantity = total_quantity
            product.arrived_quantity = total_quantity
            product.save()

            order_total += product.price * total_quantity

        print('El total de los pedidos son: %f euros.' % order_total)

        # If producer has a defined minimum order, and it is not exceeded
        # or simply there was no order
        if (producer.minimum_order and order_total < producer.minimum_order) or order_total == 0:

            if order_total > 0:
                print('El total NO LLEGA al minimo (%f)' % producer.minimum_order)

            print('Enviando el correo de NO PEDIDO al productor...')

            # Update the product quantities and set order status
            products.update(total_quantity=Decimal(
                0), arrived_quantity=Decimal(0), sent_to_producer=True)
            models.Order.objects.filter(product__in=products).update(
                status=models.STATUS_MIN_ORDER_NOT_MET)

            # Inform producer that their minimum order was not met
            email_subject = "[BroquilGotic]Aquest cop no arribem al mínim per a fer la comanda"""
            html_content = 'Ho sentim molt'

            # If there is an email template stored in DB, use it
            email = models.EmailTemplate.objects.filter(
                email_code=models.EMAIL_PRODUCER_NO_ORDER).first()

            if email:
                print("NO PEDIDO email plantilla encontrada en el base de datos.")
                email_subject = email.full_subject()
                html_content = email.body

            libs.send_email_to_address(
                email_subject, html_content, [producer.email])

            print('NO PEDIDO email enviado correctamente.')
            # Skip to next producer
            continue

        # Prepare and send the email to the producer
        print('Enviando el correo de TOTAL DEL PEDIDO al productor...')
        email_subject = '[BroquilGotic]Comanda del Broquil del Gòtic'
        html_content = '[[CONTENT]]'

        # If there is an email template stored in DB, use it
        email = models.EmailTemplate.objects.filter(
            email_code=models.EMAIL_PRODUCER_ORDER_TOTAL).first()
        if email:
            print("TOTAL DEL PEDIDO email plantilla encontrada en el base de datos.")
            email_subject = email.full_subject()
            html_content = email.body

        order_totals_table = """<table border="1" cellpadding="2"
            cellspacing="0">
            <tr><th>Producte</th><th>Quantitat</th></tr>"""

        for product in products:
            if product.total_quantity > 0:
                order_totals_table += '<tr><td>%s</td><td>%s</td></tr>' % \
                                      (product.name, str(product.total_quantity))

        order_totals_table += '</table>'

        # Fill in the email with offer summary and send to active users
        html_content = html_content.replace(
            "[[CONTENT]]", order_totals_table)
        libs.send_email_to_address(
            email_subject, html_content, [producer.email])
        products.update(sent_to_producer=True)

        print('TOTAL DEL PEDIDO email enviado correctamente.')

    # If some orders were processed in this run
    if some_orders_processed:
        # Check if there are any remaining products for this distribution
        # date
        products = models.Product.objects.filter(
            sent_to_producer=False, distribution_date=next_dist_date)

        # If there are no remaining products, send the emails to the
        # members
        if len(products) == 0:
            print(
                """No quedan mas productos en la oferta."""
                """Informando los miembros de que el pedido """
                """se ha enviado a los productores.""")

            email_subject = '[BroquilGotic]S\'ha fet la comanda!!'
            html_content = \
                """<p>S\'ha fet la comanda, pots passar a recollirla """ \
                """el Dimecres.</p><p>[[CONTENT]]</p>""" \
                """<p>Salut!! amb el broquil :P<br></p>"""

            # If there is an email template stored in DB, use it
            email = models.EmailTemplate.objects.filter(
                email_code=models.EMAIL_ORDER_SENT_TO_PRODUCER).first()
            if email:
                print(
                    """PEDIDO ENVIADO AL PRODUCTOR email plantilla """
                    """encontrada en el base de datos.""")
                email_subject = email.full_subject()
                html_content = email.body

            extra_information = ''
            # TODO ADD INFORMATION ABOUT PRODUCTS FOR WHICH MIN ORDER
            # WAS NOT MET!
            # 'Malauradament, no hem fet prou Encarrecs per demanar
            # els seguents productes:'

            html_content = html_content.replace(
                "[[CONTENT]]", extra_information)

            result = libs.send_email_to_active_users(
                email_subject, html_content)
            print(
                """PEDIDO ENVIADO AL PRODUCTOR email enviado """
                """a %d personas.""" % result[0])


def create_offer():
    # Check if there will be an offer this week (exclude today in case
    # it is Wednesday)
    next_dist_date = libs.get_next_distribution_date(False)

    days_until_next_distribution = (next_dist_date - libs.get_today()).days

    # If there is more than one week until next distribution date,
    # do not create offer
    if days_until_next_distribution > 7:
        print(
            """Quedan %d dias para la proxima fecha de distribucion """
            """(%s). NO se creara la oferta.""" %
            (days_until_next_distribution,
             next_dist_date.strftime('%d/%m/%Y')))
        return

    # Get Cal Rosset producer record, read the excel
    # and parse the products
    cal_rosset = models.Producer.objects.filter(
        excel_format=models.CAL_ROSSET).first()

    # Fetch Cal Rosset excel file from Gmail and get the local file path
    print('Intentando descargar el excel del productor principal...')

    excel_file_path = download_cal_rosset_excel()

    if excel_file_path == "":
        print('Problema al descargar el excel del productor principal.')
        return

    print('El excel se ha descargado correctamente.')

    book = xlrd.open_workbook(excel_file_path)
    products = parser.parse_cal_rosset(book)

    # In a transaction
    with transaction.atomic():
        # Delete old products from the same producer
        models.Product.objects.filter(
            distribution_date=None,
            category__producer_id=cal_rosset.id).delete()

        # Insert new products one by one
        for product in products:
            category_text = product[0]
            name_text = product[1].strip()
            price_text = str(product[2]).replace(',', '.')
            unit_text = product[3]
            origin_text = product[4]
            comments_text = product[5]

            # Clean the unit text and remove currency char and extra chars
            unit_text = unit_text \
                .replace('€', '') \
                .replace('*', '') \
                .replace('/', '').strip()

            # If comments include the word unitat, or the unit is not kilos
            # the demand should be made in units
            integer_demand = "unitat" in comments_text.lower() or unit_text.lower() != "kg"

            # For some exceptions, update the integer_demand value
            for exceptional_product in [
                "carabassa",
                "carbassa",
                "síndria",
                "meló",
                "mango"]:
                integer_demand = integer_demand or exceptional_product in name_text.lower()

            category, _ = models.Category.objects.get_or_create(
                name=category_text,
                producer_id=cal_rosset.id)

            # Create and save the product
            prod = models.Product(
                name=name_text,
                category_id=category.id,
                origin=origin_text,
                comments=comments_text,
                price=Decimal(price_text),
                unit=unit_text,
                integer_demand=integer_demand)
            prod.save()

        print(
            'Se han importado %d productos del productor principal.' %
            len(products))

    # Update/duplicate available products to create the final offer
    producers = models.Producer.objects.filter(active=True)

    for producer in producers:
        print(
            'Comprobando productor: %s...' %
            producer.company_name)

        producer_next_dist_date = \
            libs.get_producer_next_distribution_date(producer.id, False)

        # If this producer is not available in the next dist date, skip it
        if producer_next_dist_date != next_dist_date:
            print(
                """Para este productor, la proxima fecha de """
                """distribucion es: %s, saltando el productor.""" %
                producer_next_dist_date.strftime('%d/%m/%Y'))
            continue

        print('Creando oferta del productor.')

        producer_last_dist_date = \
            libs.get_producer_last_distribution_date(producer.id, True)
        limit_date = \
            libs.get_producer_order_limit_date(producer, next_dist_date)

        # Choose the products with empty distribution dates
        products = models.Product.objects.filter(
            category__producer=producer,
            distribution_date__isnull=True,
            archived=False)

        if products:
            print(
                'El productor tiene %d productos...' %
                len(products))

            # Delete all products already copied for this week
            models.Product.objects.filter(
                category__producer=producer,
                distribution_date=next_dist_date,
                sent_to_producer=False).delete()

            # Update fields and save as new record
            with transaction.atomic():
                for product in products:
                    # If producer has fixed products, clear the primary key
                    # so that product is duplicated
                    # Else, product is overwritten
                    if producer.fixed_products:
                        product.pk = None

                    product.order_limit_date = limit_date
                    product.distribution_date = next_dist_date

                    # For producers with limited availability, copy
                    # the average ratings from last distribution
                    if producer.limited_availability:
                        prev_product = models.Product.objects.filter(
                            category__producer=producer,
                            distribution_date=producer_last_dist_date,
                            name=product.name,
                            origin=product.origin).first()

                        if prev_product:
                            product.average_rating = \
                                prev_product.average_rating
                        else:
                            product.average_rating = 0
                            product.new_product = True
                    # For other producers, ratings will be updated
                    # automatically when products are rated
                    else:
                        product.average_rating = 0

                        # If there is not any product with same name and
                        # origin from last week
                        prev_product = models.Product.objects.filter(
                            category__producer=producer,
                            distribution_date=producer_last_dist_date,
                            name=product.name,
                            origin=product.origin)

                        # Mark product as new
                        if prev_product.count() == 0:
                            product.new_product = True

                    product.save()

            print(
                'Los productos se han definido correctamente.')

    # Send the reminder email to the active members
    print(
        """Enviando el correo de informacion sobre la oferta """
        """a los miembros...""")

    # Prepare the offer summary with short explanation of each
    # available producer
    offer_summary = ""
    producers = models.Producer.objects.filter(
        category__product__order_limit_date__gt=libs.get_now()).distinct()

    for producer in producers:
        # Add information of these products to the offer summary included
        # in the email sent to members
        limit_date = \
            libs.get_producer_order_limit_date(producer, next_dist_date)
        offer_summary += \
            '<li>%s (fins %s)</li>' % \
            (producer.short_product_explanation,
             timezone.localtime(limit_date).strftime("%d/%m/%Y %H:%M"))

    email_subject = '[BroquilGotic]Oferta d\'aquesta setmana'
    html_content = \
        """<p style="text-align: center;">""" \
        """<strong><u>El Bróquil Del Gótic</u></strong>""" \
        """</p>""" \
        """<p style="text-align: left; ">Hola broquilire!!!!</p>""" \
        """<p style="text-align: left; ">Aquesta setmana pots comprar """ \
        """aquests maravellosos productes!:</p>""" \
        """<h4 style="text-align: left; ">""" \
        """<b>[[CONTENT]]</b>""" \
        """</h4>""" \
        """<p style="text-align: left;">Ja pots fer la teva""" \
        """<strong>comanda</strong>""" \
        """<a href="https://el-broquil.rhcloud.com">aquí</a></p>"""

    offer_summary = "<ul>" + offer_summary + "</ul>"

    # If there is an email template stored in DB, use it
    email = models.EmailTemplate.objects.filter(
        email_code=models.EMAIL_OFFER_CREATED).first()

    if email:
        print(
            """OFERTA CREADA email plantilla encontrada en el base """
            """de datos.""")
        email_subject = email.full_subject()
        html_content = email.body

    # Fill in the email with offer summary and send to active users
    html_content = html_content.replace("[[CONTENT]]", offer_summary)

    result = libs.send_email_to_active_users(email_subject, html_content)

    print(
        'OFERTA CREADA email enviado a %d personas.' %
        result[0])
    os.remove(excel_file_path)


def download_cal_rosset_excel():
    counter = 0
    # Directory where to save attachments (default: current)
    detach_dir = os.path.join(settings.BASE_DIR, 'data', 'temp')

    # Check offer emails sent in the last 5 days
    limit = (datetime.now() - timedelta(days=5)).strftime('%d-%b-%Y')
    email_from = "comandes@calrosset.com"

    # Connect to the Gmail IMAP server
    user = settings.EMAIL_HOST_USER
    pwd = settings.EMAIL_HOST_PASSWORD

    print('>Connectando a GMAIL')
    # m = imaplib.IMAP4_SSL("imap.gmail.com")
    m = imaplib.IMAP4_SSL("74.125.133.109")
    m.login(user, pwd)

    # Choose the "All mail" folder
    m.select('"[Gmail]/Tot el correu"')

    # Search for the offer emails (subject='oferta cal rosset' and
    # sent in the last few days)
    _, items = m.search(None, f'(SINCE "{limit}") (FROM "{email_from}")')
    items = items[0].split()  # getting the mails id

    file_path = ""

    if len(items) == 0:
        print(f">Ningun email encontrado con el FROM: '{email_from}'.")
        return ""

    print(f">{len(items)} emails encontrados con el FROM: '{email_from}'.")

    for emailid in items:
        # Get the email
        _, data = m.fetch(emailid, "(RFC822)")
        email_body = data[0][1]
        mail = email.message_from_bytes(email_body)
        # Only process mails with attachments
        if mail.get_content_maintype() != 'multipart':
            continue

        print(f"Mail con tema '{mail['Subject']}', con fecha '{mail['Date']}'")
        # Iterate over mail parts
        for part in mail.walk():
            # Multipart are just containers, so we skip them
            if part.get_content_maintype() == 'multipart':
                continue

            # Is this part an attachment ?
            if part.get('Content-Disposition') is None:
                continue

            # Get attachment filename
            filename = part.get_filename()

            # If there is no filename, we create one with a counter
            # to avoid duplicates
            if not filename:
                filename = 'part-%03d%s' % (counter, 'bin')
                counter += 1

            if "xls" not in filename:
                continue

            file_path = os.path.join(detach_dir, filename)

            print('Saving file %s.' % filename)
            # finally write the stuff
            fp = open(file_path, 'wb')
            fp.write(part.get_payload(decode=True))
            fp.close()

    return file_path


def send_sunday_reminder():
    print('Enviando el recordatorio a los miembros...')

    if models.Product.objects.filter(
            distribution_date=libs.get_next_weekday()).count() == 0:
        print(
            """No productos en oferta para este miercoles, """
            """no se enviara ningun correo...""")
        return

    # Send the reminder email to the active members
    email_subject = '[BroquilGotic]No t\'oblidis de fer la comanda'
    html_content = \
        """Hola broquilire!!!!<br/>""" \
        """<br/>""" \
        """Tant sols recordar-te que pots fer la comanda fins el """ \
        """Diumenge nit """ \
        """<a href=\"http://broquilgotic.pythonanywhere.com\">aqu&iacute;</a> """ \
        """i que pots recullir la comanda el <em>Divendres</em> de """ \
        """<strong>18 a 19:30</strong>, no ho deixis correr ;)<br/>""" \
        """<br/>""" \
        """Tamb&eacute; que necessitem que t'apuntis a les """ \
        """ permanencies en el sistema :P<br/>""" \
        """<br/>""" \
        """Salut!! amb el broquil :P<br/>"""

    # If there is an email template stored in DB, use it
    email = models.EmailTemplate.objects.filter(
        email_code=models.EMAIL_REMINDER).first()

    if email:
        print(
            'RECORDATORIO email plantilla encontrada en el base de datos.')
        email_subject = email.full_subject()
        html_content = email.body

    result = libs.send_email_to_active_users(email_subject, html_content)

    print(
        'RECORDATORIO email enviado a %d personas.' % result[0])


def send_task_reminder():
    print(
        'Enviando el recordatorio a los responsables de permanencia...')

    now = libs.get_now()

    # Update the distribtion task information from Google Calendar
    update_log = libs.update_distribution_task_information(now.year)
    print(update_log)

    # If we are in December, update next year's information too
    if now.month == 12:
        update_log = libs.update_distribution_task_information(now.year + 1)
        print(update_log)

    # Check if there is a distribution task in the following 9 days (larger
    # margin to handle modified dist. dates)
    some_days_later = now + timedelta(days=9)
    tasks = models.DistributionTask.objects.filter(
        distribution_date__lt=some_days_later,
        distribution_date__gt=now) \
        .prefetch_related('user', 'user__extrainfo')

    if tasks.count() == 0:
        print(
            """No hay permanencias en los proximos dias, """
            """no se enviara ningun correo...""")
        return

    task_date = tasks.first().distribution_date

    # Send the reminder email to the active members
    email_subject = '[BroquilGotic]Recordatori de Perman&egrave;ncies'
    html_content = \
        """Hola,<br/>""" \
        """<br/>""" \
        """Et recordem que el dia [[CONTENT]] et toca """ \
        """perman&egrave;ncia.<br/>""" \
        """Aqu&iacute; tens el """ \
        """<a href='https://docs.google.com/document/d/""" \
        """1HiO933Eh_00ftbK8qTpBv09OKTkcIIqD4IdRov1qxhA/edit'> """ \
        """manual d'instruccions</a> i """ \
        """<a href='https://vimeo.com/117321849'>""" \
        """video explicatiu</a> per si de cas.<br/>""" \
        """<br/>""" \
        """<strong>La perman&egrave;ncia comen&ccedil;a a les 17h i """ \
        """acaba a les 20h. Poseu-vos d'acord fent un &quot;responder""" \
        """ a todos&quot; amb la confirmaci&oacute; de la teva """ \
        """disponibilitat i l'hora prevista d'arribada.</strong>""" \
        """<br/><br/>""" \
        """L'equip d'aquesta setmana el formeu 3 persones; una de """ \
        """vosaltres ha de tenir la clau de la Negreta. Si no la """ \
        """ teniu, truqueu a l'Aina: 677 652 245.<br/>""" \
        """<br/>""" \
        """Per a qualsevol atre problema que pugueu tenir, truqueu a """ \
        """l'Aina, que estar&agrave; pendent i a prop ;).<br/>""" \
        """<br/>""" \
        """A reveure i Salut!<br/>""" \
        """<br/>""" \
        """In&egrave;s, Bel&egrave;n i Aina"""

    # If there is an email template stored in DB, use it
    email = models.EmailTemplate.objects.filter(
        email_code=models.EMAIL_TASK_REMINDER).first()

    if email:
        print(
            'RECORDATORIO email plantilla encontrada en el base de datos.')
        email_subject = email.full_subject()
        html_content = email.body

    html_content = html_content.replace(
        "[[CONTENT]]", task_date.strftime('%d/%m/%Y'))
    to = []
    cc = []

    # Add the email addresses for members that have a task this week
    for task in tasks:
        to.append(task.user.email)

        # Try to see if there is a second email address for the user and
        # add it if necessary
        try:
            if task.user.extrainfo.secondary_email and \
                            len(task.user.extrainfo.secondary_email) > 0:
                to.append(task.user.extrainfo.secondary_email)
        except ObjectDoesNotExist:
            pass

    cc_lists = models.EmailList.objects.filter(cc_task_reminders=True)

    # For all CC lists, add the email addresses to CC
    for cc_list in cc_lists:
        for email_address in \
                cc_list.email_addresses.replace(' ', ',').split(','):
            if email_address != "":
                cc.append(email_address)

    libs.send_email_with_cc(email_subject, html_content, to, cc)

    print(
        'RECORDATORIO email enviado a %d personas.' % len(to))


if __name__ == "__main__":
    download_cal_rosset_excel()
