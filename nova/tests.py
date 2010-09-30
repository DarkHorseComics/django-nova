import re
from datetime import datetime

from django.test import TestCase
from django.core import mail
from django.core.urlresolvers import reverse

from nova.models import Subscription, TOKEN_LENGTH

def _make_subscription(email):
    return Subscription.objects.create_with_random_token(email)

class TestModel(TestCase):
    def test_token_autogen(self):
        sub1 = _make_subscription('test1@example.com')
        sub2 = _make_subscription('test2@example.com')
        self.assertTrue(sub1.token is not None)
        self.assertTrue(sub2.token is not None)
        self.assertNotEqual(sub1.token, sub2.token)

    def test_auto_signup_ts(self):
        ts = datetime.now()
        sub = _make_subscription('test@example.com')
        sub.confirmed = True
        sub.save()
        sub = Subscription.objects.get(pk=sub.pk)
        self.assertTrue(sub.confirmed_at is not None)
        self.assertTrue(sub.confirmed_at > ts)

class TestViews(TestCase):
    def _do_subscribe(self, email):
        subscribe_url = reverse('nova.views.subscribe')
        params = {'email': email}
        return self.client.post(subscribe_url, params, follow=True)

    def test_subscribe(self):
        existing_subs = Subscription.objects.all().count()
        email = 'test_subscribe@example.com'
        response = self._do_subscribe(email=email)
        self.assertTrue(email in response.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('confirm' in mail.outbox[0].body)
        self.assertEqual(Subscription.objects.all().count(), existing_subs + 1)

    def test_confirm(self):
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

