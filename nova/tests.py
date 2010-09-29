import re

from django.test import TestCase
from django.core import mail
from django.core.urlresolvers import reverse

from nova.models import Subscription, TOKEN_LENGTH

class TestTokenGeneartion(TestCase):
    def test_token_autogen(self):
        sub1 = Subscription.objects.create_with_random_token(email='test1@example.com')
        sub2 = Subscription.objects.create_with_random_token(email='test2@example.com')
        self.assertTrue(sub1.token is not None)
        self.assertTrue(sub2.token is not None)
        self.assertNotEqual(sub1.token, sub2.token)

class TestSignup(TestCase):
    def _do_subscribe(self, email):
        return self.client.post(reverse('nova.views.subscribe'), {'email': email})

    def test_subscribe(self):
        email = 'test_subscribe@example.com'
        response = self._do_subscribe(email=email)
        self.assertTrue(email in response.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('confirm' in mail.outbox[0].body)

        subscription = Subscription.objects.get(email=email)

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


