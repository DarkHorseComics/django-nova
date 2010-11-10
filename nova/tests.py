"""
Basic unit and functional tests for newsletter signups
"""
import re
from datetime import datetime

from django.test import TestCase
from django.core import mail
from django.core.urlresolvers import reverse

from nova.models import Subscription, TOKEN_LENGTH

def _make_subscription(email):
    return Subscription.objects.create_with_random_token(email)

class TestSubscriptionModel(TestCase):
    """
    Model API unit tests
    """
    def test_token_autogen(self):
        """
        Verify that tokens are assigned automatically to each subscription
        """
        sub1 = _make_subscription('test1@example.com')
        sub2 = _make_subscription('test2@example.com')
        self.assertTrue(sub1.token is not None)
        self.assertTrue(sub2.token is not None)
        self.assertNotEqual(sub1.token, sub2.token)

    def test_auto_signup_ts(self):
        """
        Check that confirmation timestamps are auto-assigned
        """
        ts = datetime.now()
        sub = _make_subscription('test@example.com')
        sub.confirmed = True
        sub.save()
        sub = Subscription.objects.get(pk=sub.pk)
        self.assertTrue(sub.confirmed_at is not None)
        self.assertTrue(sub.confirmed_at > ts)

class TestSignupViews(TestCase):
    """
    Functional tests for newsletter signup views
    """
    def _do_subscribe(self, email):
        subscribe_url = reverse('nova.views.subscribe')
        params = {'email': email}
        return self.client.post(subscribe_url, params, follow=True)

    def test_subscribe(self):
        """
        Test that a new subscription is created for each POST to the 
        'subscription' view, and that the generated email includes the posted
        email address.

        Note: this test can fail if a site template override does not include
        the email address in its message body.
        """
        existing_subs = Subscription.objects.all().count()
        email = 'test_subscribe@example.com'
        response = self._do_subscribe(email=email)
        self.assertTrue(email in response.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('confirm' in mail.outbox[0].body)
        self.assertEqual(Subscription.objects.all().count(), existing_subs + 1)

    def test_confirm(self):
        """
        Ensure that the confirmation URL returned in the subscription email 
        automatically confirms the model instance when loaded via GET.
        """
        email = 'test_confirm@example.com'
        response = self._do_subscribe(email=email)

        subscription = Subscription.objects.get(email=email)
        confirm_url = reverse('nova.views.confirm', args=(subscription.token,))

        message = mail.outbox[0].body
        self.assertTrue(confirm_url in message)
        
        response = self.client.get(confirm_url)
        self.assertTrue(email in response.content)

        subscription = Subscription.objects.get(pk=subscription.pk)
        self.assertTrue(subscription.confirmed)

    def test_unsubscribe(self):
        """
        Test that a subscription is marked unconfirmed for each post to the
        'unsubscribe' view.
        """
        # Create subscription
        email = 'test_confirm@example.com'
        self._do_subscribe(email=email)

        # Confirm subscription
        subscription = Subscription.objects.get(email=email)
        confirm_url = reverse('nova.views.confirm', args=(subscription.token,))
        self.client.get(confirm_url)

        # Assert we have a confirmed subscription
        self.assertEqual(Subscription.objects.filter(confirmed=True).count(), 1)

        # Test unsubscribe view
        unsubscribe_url = reverse('nova.views.unsubscribe', args=(subscription.token,))
        response = self.client.get(unsubscribe_url)

        # Test unsubscribe
        response = self.client.post(unsubscribe_url)
        self.assertEqual(Subscription.objects.filter(confirmed=True).count(), 0)
