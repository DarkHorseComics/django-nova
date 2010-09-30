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
        return self.client.post(reverse('nova.views.subscribe'), {'email': email})

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

        confirm_url = reverse('nova.views.confirm')
        url_pat = r'\s(https?://{0}.*)\s'.format(confirm_url)
        match = re.search(url_pat, mail.outbox[0].body)
        self.assertTrue(match is not None)
        
        full_url = match[0]
        response = self.client.get(full_url)
        self.assertTrue(email in response.body)

        subscription = Subscription.objects.get(email=email)
        self.assertTrue(subscription.confirmed)

