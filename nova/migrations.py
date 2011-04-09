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
            
            
class AddDjangoUserAccounts(Migration):
    """
    Save all confirmed EmailAddresses, so we get new user accounts
    """
    def apply(self, *args, **kwargs):
        for address in EmailAddres.objects.filter(confirmed=True):
            #save should set the user attribute
            address.save()
