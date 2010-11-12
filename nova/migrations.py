from finch.base import Migration, SqlMigration

from nova.models import EmailAddress, Subscription

class AddClientAddr(SqlMigration):
    sql = "ALTER TABLE {table} ADD COLUMN client_addr VARCHAR(16)"

    class Meta:
        model = Subscription


class CreateEmailAddressFromSubscription(Migration):
    """
    Migrate email, token, client_addr, confirmed and
    created_at from Subscription model to EmailAddress model.
    """
    def apply(self, db, db_table):
        for subscription in Subscription.objects.all():
            email_address = EmailAddress()
            email_address.email = subscription.email
            email_address.token = subscription.token
            email_address.client_addr = subscription.client_addr
            email_address.confirmed = subscription.confirmed
            email_address.confirmed_at = subscription.confirmed_at
            email_address.save()
            # Preserve original created_at date
            email_address.created_at = subscription.created_at
            email_address.save()


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
