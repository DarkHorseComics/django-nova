"""
"""
from optparse import make_option

from django.core.management.base import BaseCommand,CommandError
from django.contrib.humanize.templatetags.humanize import intcomma

from nova.models import EmailAddress

class Command(BaseCommand):
    help = 'This command is used to bulk unsubscribe subscribers from django-nova.'

    option_list = BaseCommand.option_list + (
        make_option('-f', '--file', dest='filename',
            help='A file containing a newline separated list of email addresses.'),
        make_option('-d', '--delete', action="store_true", default=False,
            dest='delete_emails', help='If set will delete addresses instead of simply unsubscribing them.'),
        make_option('--verbose', action="store_true", default=False,
            dest='verbose', help='Toggle verbose output.'),
    )

    def handle(self, *args, **options):
        verbose = options.get('verbose')
        filename = options.get('filename')
        delete_emails = options.get('delete_emails')

        # Filename is required
        if filename is None:
            raise CommandError("You must use -f FILENAME or --file=FILENAME to specify a list of emails.")

        try:
            # Keep a count of emails successfully processed
            count = 0
            with open(filename, 'r') as f:
                for line in f:
                    email = line.strip()

                    if verbose:
                        print "Unsubscribing \"%s\"..." % email

                    try:
                        address = EmailAddress.objects.get(email=email)
                        if delete_emails:
                            address.delete()
                        else:
                            address.unsubscribe()

                        count += 1
                    except EmailAddress.DoesNotExist:
                        if verbose:
                            print "Email address \"%s\" does not exist!" % email
        except IOError as (errno, strerror):
            raise CommandError("%s" % strerror)

        if delete_emails:
            print "\nDeleted %s email addresses." % (intcomma(count),)
        else:
            print "\nUnsubscribed %s email addresses." % (intcomma(count),)
