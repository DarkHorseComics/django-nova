"""
A command to send reminders to unconfirmed addresses
"""

from optparse import make_option

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand,CommandError

from nova.views import _send_message
from nova.models import EmailAddress

class Command(BaseCommand):
    help = "Send reminder e-mails to customers who have yet to complete their opt-in"
    
    option_list = BaseCommand.option_list + (
        make_option('-m', '--max', dest='max_reminders', 
            help='Set the maximum number of times a user should be reminded to opt-in'),
    )
    
    def handle(self, *args, **options):
        max_reminders = options.get('max_reminders', 1)
        addresses = EmailAddress.objects.filter(confirmed=False, reminders_sent__lt=max_reminders)

        current_site = Site.objects.get_current()
        
        for address in addresses:
            _send_reminder(address, current_site)
            

def _send_reminder(address, current_site):
    """
    Send a reminder message to the address provided
    """
    _send_message(
                    address.email, 
                    'nova/email/reminder_subject.txt',
                    'nova/email/reminder_body.txt',
                    {
                        'email_address': address, 
                        'site': current_site
                    }
                )
    
    address.reminders_sent = address.reminders_sent + 1
    address.save()