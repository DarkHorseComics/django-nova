"""
Basic model for a newsletter subscription, minus the newsletter (for now).
More to come...
"""
from datetime import datetime

from django.db import models
from django.forms import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _

TOKEN_LENGTH = 12

class EmailAddressManager(models.Manager):
    def create_with_random_token(self, email, **kwargs):
        """
        Generates a new (unconfirmed) email address with a random, unique token.
        Uses the underlying database uniqueness constraints to prevent race
        conditions on token creation.
        """
        instance = None

        while instance is None:
            try:
                # the `make_random_password` method returns random strings that
                # are at least somewhat readable and re-typeable
                token = User.objects.make_random_password(length=TOKEN_LENGTH)
                instance = self.create(email=email, token=token, **kwargs)
            except ValidationError:
                continue

        return instance


class EmailAddress(models.Model):
    """
    A basic model for confirmed email addresses.
    """
    email = models.EmailField(unique=True)
    user = models.ForeignKey(User, null=True, blank=True)
    token = models.CharField(null=True, blank=True, unique=True, max_length=TOKEN_LENGTH)
    client_addr = models.CharField(max_length=16, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    reminders_sent = models.PositiveIntegerField(default=0)
    
    #auto_now_add so we don't remind some user immediately after they sign up
    reminded_at = models.DateTimeField(auto_now_add=True)
    
    objects = EmailAddressManager()

    def save(self, *args, **kwargs):
        """
        Set confirmed_at when this instance is confirmed.
        """
        if self.confirmed and self.confirmed_at is None:
            self.confirmed_at = datetime.now()
        super(EmailAddress, self).save(*args, **kwargs)

    @property
    def get_confirm_url(self):
        """
        Returns the unique confirmation URL for this email address,
        suitable for use in follow-up emails.
        """
        return reverse('nova.views.confirm', args=(self.token,))

    def __unicode__(self):
        """
        String-ify this email address
        """

        if self.confirmed:
            status = u'confirmed'
        else:
            status = u'unconfirmed'

        return u'{0} ({1})'.format(self.email or 'None', status)

    class Meta:
        verbose_name_plural = 'Email Addresses'


class Newsletter(models.Model):
    """
    A basic newsletter model.
    """
    title = models.CharField(max_length=255, null=False, blank=False)
    active = models.BooleanField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    approvers = models.TextField(null=True, blank=True,
                                 help_text=_("A whitespace separated list of email addresses."))

    subscriptions = models.ManyToManyField(EmailAddress, through='Subscription')

    @property
    def subscribers(self):
        """
        Return a list of confirmed subscribers.
        """
        return self.subscriptions.filter(confirmed=True)

    def __unicode__(self):
        """
        String-ify this newsletter 
        """
        return u'%s' % self.title


class NewsletterIssue(models.Model):
    """
    An issue of a newsletter. This model wraps the actual email subject
    line and template that will be sent out to subscribers.
    """
    subject = models.CharField(max_length=255, null=False, blank=False)
    body = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    newsletter = models.ForeignKey(Newsletter)

    def send(self):
        """
        Sends this issue to subscribers of this newsletter. 
        """
        subscriptions = self.newsletter.subscribers
        if subscriptions.count() > 0:
            for subscription in subscriptions:
                send_to = subscription.email
                send_mail(self.subject, self.body, settings.DEFAULT_MAIL_FROM, (send_to,))
    
    def send_test(self):
        """
        Sends this issue to an email address specified by an admin user
        """
        approvers = self.newsletter.approvers.split()
        if len(approvers) > 0:
            for email in approvers:
                send_to = email
                subject = self.subject
                body = """\
                *** This is only a test. If actually sent, this message would go to {subscribers} subscribers ***
                {body}""".format(subscribers=self.newsletter.subscribers.count(), body=self.body)
                send_mail(subject, body, settings.DEFAULT_MAIL_FROM, (send_to,))

    def __unicode__(self):
        """
        String-ify this newsletter issue
        """
        return u'%s' % self.subject


class Subscription(models.Model):
    """
    This model subscribes an EmailAddress instance to a Newsletter instance.
    """
    email_address = models.ForeignKey(EmailAddress, related_name='subscriptions')
    newsletter = models.ForeignKey(Newsletter)
    active = models.BooleanField(null=False, blank=False, default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        """
        String-ify this subscription
        """
        return u'{email} to {newsletter})'.format(email=self.email_address.email,
                                                  newsletter=self.newsletter)
