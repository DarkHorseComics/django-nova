from django.conf import settings
from django.db import connection

from finch.base import Migration, SqlMigration
from nova.models import *

class AddClientAddr(SqlMigration):
    sql = "ALTER TABLE {table} ADD COLUMN client_addr VARCHAR(16)"

    class Meta:
        model = Subscription

class CreateEmailAddressFromSubscription(SqlMigration):
    """
    Migrate data from subscription table to emailaddress
    table.
    """
    sql = """\
    INSERT INTO nova_emailaddress (
        email,
        token,
        client_addr,
        confirmed,
        confirmed_at,
        created_at
    )
    SELECT email,
    token,
    client_addr,
    confirmed,
    confirmed_at,
    created_at
    FROM nova_subscription"""


class DropSubscriptionTable(SqlMigration):
    """
    This migration drops the subscription table and will
    require running a syncdb after migrations have finished
    in order to recreate the new model structure.
    """
    sql = """\
    DROP TABLE {table}"""

    class Meta:
        model = Subscription
        requires = [CreateEmailAddressFromSubscription]
        

class AddRemindersSent(SqlMigration):
    """
    Adds a reminders_sent column to the EmailAddress table
    """
    sql = """
        ALTER TABLE {table} ADD COLUMN reminders_sent integer DEFAULT 0
    """
    
    class Meta: 
        model = EmailAddress
        
class AddRemindedAt(SqlMigration):
    sql = """
        ALTER TABLE {table} ADD COLUMN reminded_at timestamp with time zone
    """
    
    class Meta: 
        model = EmailAddress
    
class RenameBodyField(SqlMigration):
    sql = """
    ALTER TABLE {table} RENAME COLUMN body TO template"""

    class Meta:
        model = NewsletterIssue

class AddDefaultTemplateField(SqlMigration):
    sql = """
    ALTER TABLE {table} ADD COLUMN default_template VARCHAR(255)"""

    class Meta:
        model = Newsletter

class AddLinkTrackingFields(SqlMigration):
    sql = """
    ALTER TABLE {table}
    ADD COLUMN track integer DEFAULT 1,
    ADD COLUMN tracking_term VARCHAR(20),
    ADD COLUMN tracking_campaign VARCHAR(20)"""

    class Meta:
        model = NewsletterIssue

class FixTrackField(SqlMigration):
    sql = """
    ALTER TABLE {table}
    DROP COLUMN track,
    ADD COLUMN track boolean DEFAULT True NOT NULL
    """

    class Meta:
        model = NewsletterIssue
        requires = [AddLinkTrackingFields]

class RemoveInvalidEmailAddresses(Migration):
    """
    Delete any invalid and unconfirmed email addresses
    that snuck into the database.
    """
    def apply(self, *args, **kwargs):
        for address in EmailAddress.objects.all():
            try:
                if not _email_is_valid(address.email):
                    if not address.confirmed:
                        address.delete()
                    else:
                        print "Invalid, but confirmed: %s [pk=%d]" % (address, address.pk)
            except:
                pass

class RemoveInactiveSubscriptions(Migration):
    """
    Delete any newsletter subscriptions that are
    not active.
    """
    def apply(self, *args, **kwargs):
        for subscription in Subscription.objects.filter(active=False):
            subscription.delete()
            
class AddNewsletterIssueFields(SqlMigration):
    """
    Add the sent_at and rendered_template fields to the
    NewsletterIssue model.
    """
    sql = """\
    ALTER TABLE {table}
    ADD COLUMN rendered_template text NOT NULL DEFAULT '',
    ADD COLUMN sent_at timestamp DEFAULT NULL"""

    class Meta:
        model = NewsletterIssue

class AddNewsletterFields(SqlMigration):
    """
    Add the from_email and reply_to_email fields to the
    Newsletter model.
    """
    sql = """\
    ALTER TABLE {table}
    ADD COLUMN from_email VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN reply_to_email VARCHAR(255) NOT NULL DEFAULT ''"""

    class Meta:
        model = Newsletter

class AddDefaultNewsletterFromEmail(Migration):
    """
    Populate existing newsletters with a default from_email
    address.
    """
    def apply(self, *args, **kwargs):
        for newsletter in Newsletter.objects.all():
            newsletter.from_email = settings.NOVA_FROM_EMAIL
            newsletter.save()

    class Meta:
        requires = [AddNewsletterFields,]

class UpdateNewsletterTrackingFields(SqlMigration):
    """
    Add the tracking_domain field and drop the tracking_term
    field on the NewsletterIssue model.
    """
    sql = """\
    ALTER TABLE {table}
    ADD COLUMN tracking_domain VARCHAR(255) NOT NULL DEFAULT '',
    DROP COLUMN tracking_term"""

    class Meta:
        model = NewsletterIssue

class RemoveDuplicateEmails(Migration):
    """
    Generate a list of duplicate email addresses,
    remove duplicates, but persist the latest entry.
    """
    def apply(self, *args, **kwargs):
        # Get list of duplicates
        cursor = connection.cursor()
        cursor.execute('SELECT UPPER(email) FROM nova_emailaddress GROUP BY UPPER(email) HAVING COUNT(UPPER(email)) > 1')
        email_addresses = cursor.fetchall()

        print 'Fixing %d duplicate emails...' % (len(email_addresses))

        # Iterate over duplicates
        for email in email_addresses:
            dupes = EmailAddress.objects.filter(email__iexact=email[0]).order_by('-created_at')

            # Get the newest object
            first = dupes[0]

            # Check for a confirmed dupe
            confirmed = False
            for email in dupes:
                if email.confirmed:
                    confirmed = True

            # Delete all duplicates
            dupes.exclude(pk=first.pk).delete()

            # Persist confirmed
            first.confirmed = confirmed
            first.save()

class NormalizeEmailAddresses(Migration):
    """
    Normalize all existing email addresses by calling
    their save method.
    """
    def apply(self, *args, **kwargs):
        for email in EmailAddress.objects.all():
            email.save()

    class Meta:
        requires = [RemoveDuplicateEmails]

class AllowNullRenderedTemplate(SqlMigration):
    """
    Drop the NULL constraint on the rendered_template field on
    the NewsletterIssue model.
    """
    sql = """\
    ALTER TABLE {table}
    ALTER COLUMN rendered_template DROP NOT NULL"""

    class Meta:
        model = NewsletterIssue
        requires = [AddNewsletterIssueFields,]
