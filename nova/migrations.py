from finch.base import SqlMigration

from nova.models import Subscription

class AddClientAddr(SqlMigration):
    sql = "ALTER TABLE {table} ADD COLUMN client_addr VARCHAR(16)"

    class Meta:
        model = Subscription
