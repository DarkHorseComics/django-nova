from finch.base import Migration, SqlMigration

from nova.models import EmailAddress, Subscription

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
