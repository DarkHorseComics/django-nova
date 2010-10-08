"""
Basic model for a newsletter subscription, minus the newsletter (for now).
More to come...
"""
from datetime import datetime

from django.db import models
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

TOKEN_LENGTH = 12

class SubscriptionManager(models.Manager):
    def create_with_random_token(self, email):
        """
        Generates a new subscription request with a random, unique token.
        Uses the underlying database uniqueness constraints to prevent race
        conditions on token creation.
        """
        instance = None

        while instance is None:
            try:
                # the `make_random_password` method returns random strings that
                # are at least somewhat readable and re-typeable
                token = User.objects.make_random_password(length=TOKEN_LENGTH)
                instance = self.create(email=email, token=token)
            except ValidationError:
                continue

        return instance

class Subscription(models.Model):
    """
    The subscription model serves as a placeholder for a (potentially 
    unconfirmed) request to subscribe to a newsletter. Each subscription has a
    unique token that is included in follow-up emails to identify it.
    """
    email = models.EmailField(unique=True)
    token = models.CharField(null=True, blank=True, unique=True, max_length=TOKEN_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)

    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    objects = SubscriptionManager()

    def save(self, *args, **kwargs):
        """
        The `Subscription.save()` method sets the `confirmed_at` timestamp for
        any newly-confirmed subscription.
        """
        if self.confirmed and self.confirmed_at is None:
            self.confirmed_at = datetime.now()
        super(Subscription, self).save(*args, **kwargs)

    def get_confirm_url(self):
        """
        Returns the unique confirmation URL for this subscription, suitable for
        use in follow-up emails.
        """
        return reverse('nova.views.confirm', args=(self.token,))

    def __unicode__(self):
        """
        String-ify this subscription
        """

        if self.confirmed:
            status = u'confirmed'
        else:
            status = u'unconfirmed'

        return u'{0} ({1})'.format(self.email or 'None', status)
