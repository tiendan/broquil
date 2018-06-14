import sys
sys.path.append('/home/broquilgotic/broquil/')

import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'

from pytz import timezone as pytztimezone
from django.utils import timezone

from elbroquil.tasks import create_offer, send_order_to_producers, send_sunday_reminder, send_task_reminder


if __name__ == "__main__":
    weekday = timezone.now().astimezone(pytztimezone('Europe/Madrid')).date().weekday()
    
    # Send the orders to producers no matter which day it is
    print("Sending orders to producers")
    send_order_to_producers()
    
    if weekday == 4:
        # On Friday, create the offer and send task reminders
        print("Creating offer and sending task reminder")
        create_offer()
        send_task_reminder()
    elif weekday == 6:
        # On Sunday, remind people to complete their orders
        print("Sending sunday reminders")
        send_sunday_reminder()
