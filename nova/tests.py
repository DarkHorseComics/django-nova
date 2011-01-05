"""
Basic unit and functional tests for newsletter signups
"""
import re
from datetime import datetime

from django.test import TestCase
from django.core import mail, management
from django.core.urlresolvers import reverse

from nova.models import EmailAddress, Subscription, Newsletter, NewsletterIssue, TOKEN_LENGTH

def _make_newsletter(title):
    return Newsletter.objects.create(title=title)

def _make_email(email):
    return EmailAddress.objects.create_with_random_token(email)

def _make_subscription(email_address, newsletter):
    return Subscription.objects.create(email_address=email_address,
                                       newsletter=newsletter)

class TestEmailModel(TestCase):
    """
    Model API unit tests
    """
    def test_token_autogen(self):
        """
        Verify that tokens are assigned automatically to each email address
        """
        email1 = _make_email('test1@example.com')
        email2 = _make_email('test2@example.com')
        self.assertTrue(email1.token is not None)
        self.assertTrue(email2.token is not None)
        self.assertNotEqual(email1.token, email2.token)

    def test_auto_signup_ts(self):
        """
        Check that confirmation timestamps are auto-assigned
        """
        ts = datetime.now()
        email = _make_email('test@example.com')
        email.confirmed = True
        email.save()
        email = EmailAddress.objects.get(pk=email.pk)
        self.assertTrue(email.confirmed_at is not None)
        self.assertTrue(email.confirmed_at > ts)

class TestNewsletterIssueModel(TestCase):
    """
    Model API unit tests
    """
    def setUp(self):
        """
        Create a newsletter, newsletter issue and some
        subscriptions to test with.
        """
        # Create some newsletters
        self.newsletter1 = _make_newsletter("Test Newsletter 1")
        self.newsletter2 = _make_newsletter("Test Newsletter 2")

        # Create some approvers
        self.newsletter1.approvers = """\
        approver1@example.com
        approver2@example.com
        approver3@example.com
        approver4@example.com"""
        self.newsletter1.save()

        # Create an issue for each newsletter
        self.newsletter_issue1 = NewsletterIssue()
        self.newsletter_issue1.subject = 'Test Newsletter Issue 1'
        self.newsletter_issue1.body = 'Test'
        self.newsletter_issue1.newsletter = self.newsletter1
        self.newsletter_issue1.save()

        self.newsletter_issue2 = NewsletterIssue()
        self.newsletter_issue2.subject = 'Test Newsletter Issue 2'
        self.newsletter_issue2.body = 'Test'
        self.newsletter_issue2.newsletter = self.newsletter2
        self.newsletter_issue2.save()

        # Create some email addresses and subscribe them to a newsletter
        emails = ['test_email1@example.com', 'test_email2@example.com', 'test_mail3@example.com']
        for email in emails:
            email_address = EmailAddress.objects.create_with_random_token(email=email)
            email_address.confirmed = True
            email_address.save()
            Subscription.objects.create(email_address=email_address, newsletter=self.newsletter1)

        # Create an unconfirmed email address
        self.unconfirmed_email = EmailAddress.objects.create_with_random_token('test_unconfirmed@example.com')
        Subscription.objects.create(email_address=self.unconfirmed_email, newsletter=self.newsletter1)

        # Create an extra email address and subscribe it to the second newsletter
        self.exclude_email = EmailAddress.objects.create_with_random_token('test_exclude@example.com')
        self.exclude_email.confirmed = True
        self.exclude_email.save()
        Subscription.objects.create(email_address=self.exclude_email, newsletter=self.newsletter2)

    def test_send_test(self):
        """
        Verify the send_test method only sends an issue
        to the email addresses listed in the approvers field
        on the Newsletter model and doesn't blow up if approvers
        is empty.
        """
        approvers = self.newsletter1.approvers.split()
        self.assertEqual(len(approvers), 4)

        self.newsletter_issue1.send_test()

        self.assertEqual(len(mail.outbox), 4)
        
        for message in mail.outbox:
            self.assertTrue(message.to[0] in approvers)
            self.assertEqual(message.subject, self.newsletter_issue1.subject)
            self.assertTrue('This is only a test' in message.body)
            self.assertTrue(self.newsletter_issue1.body in message.body)

    def test_send(self):
        """
        Ensure that a newsletter issue is successfully sent
        to all *confirmed* subsribers of that newsletter.
        """
        self.assertEqual(self.newsletter1.subscribers.count(), 3)

        self.newsletter_issue1.send()

        self.assertEqual(len(mail.outbox), 3)

        for message in mail.outbox:
            self.assertNotEqual(self.unconfirmed_email.email, message.to[0])
            self.assertNotEqual(self.exclude_email.email, message.to[0])
            self.assertEqual(message.subject, self.newsletter_issue1.subject)

class TestSignupViews(TestCase):
    """
    Functional tests for newsletter signup views
    """
    def setUp(self):
        """
        Create a Newsletter to test against.
        """
        self.newsletter1 = _make_newsletter("Test Newsletter 1")
        self.newsletter2 = _make_newsletter("Test Newsletter 2")
        self.newsletter3 = _make_newsletter("Test Newsletter 3")

    def _do_subscribe(self, email, newsletters):
        subscribe_url = reverse('nova.views.subscribe')
        params = {'email': email,
                  'newsletters': newsletters}

        return self.client.post(subscribe_url, params, follow=True)

    def test_subscribe(self):
        """
        Test that a new subscription is created for each POST to the 
        'subscription' view, and that the generated email includes the posted
        email address.

        Note: this test can fail if a site template override does not include
        the email address in its message body.
        """
        existing_subs = Subscription.objects.count()
        email = 'test_subscribe@example.com'
        response = self._do_subscribe(email=email, newsletters=(self.newsletter1.pk,))
        self.assertTrue(email in response.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue('confirm' in mail.outbox[0].body)
        self.assertEqual(Subscription.objects.count(), existing_subs + 1)

    def test_confirm(self):
        """
        Ensure that the confirmation URL returned in the subscription email 
        automatically confirms the model instance when loaded via GET.
        """
        email = 'test_confirm@example.com'
        response = self._do_subscribe(email=email, newsletters=(self.newsletter1.pk,))

        email_address = EmailAddress.objects.get(email=email)
        confirm_url = reverse('nova.views.confirm', args=(email_address.token,))

        message = mail.outbox[0].body
        self.assertTrue(confirm_url in message)
        
        response = self.client.get(confirm_url)
        self.assertTrue(email in response.content)

        email_address = EmailAddress.objects.get(pk=email_address.pk)
        self.assertTrue(email_address.confirmed)

    def test_unsubscribe(self):
        """
        Test that a subscription is marked unconfirmed for each post to the
        'unsubscribe' view.
        """
        # Create subscription
        email = 'test_confirm@example.com'
        response = self._do_subscribe(email=email, newsletters=(self.newsletter1.pk,
                                                                self.newsletter2.pk,))

        # Confirm email address
        email_address = EmailAddress.objects.get(email=email)
        confirm_url = reverse('nova.views.confirm', args=(email_address.token,))
        self.client.get(confirm_url)

        # Assert we have a confirmed email
        self.assertEqual(EmailAddress.objects.filter(confirmed=True).count(), 1)

        # Assert this email has the correct number of subscriptions
        self.assertEqual(Subscription.objects.filter(email_address=email_address, active=True).count(), 2)

        # Test unsubscribe view
        unsubscribe_url = reverse('nova.views.unsubscribe', args=(email_address.token,))
        response = self.client.get(unsubscribe_url)

        # Test unsubscribe
        response = self.client.post(unsubscribe_url)
        self.assertEqual(Subscription.objects.filter(email_address=email_address, active=False).count(), 2)
        

class TestManagement(TestCase):
    """
    Test functions related to nova's management commands
    """
    def setUp(self):
        """
        create some unconfirmed emails
        """
        self.email = _make_email('test@tfaw.com')
        self.email2  = _make_email('test2@tfaw.com')
        self.email2.reminders_sent=1
        self.email2.save()
        
    def test_send_reminders(self):
        """
        Ensure the send_reminders command works as expected
        """
        self.assertEqual(self.email.reminders_sent, 0)
        management.call_command('send_reminders')
        
        self.email = EmailAddress.objects.get(pk=self.email.pk)
        self.email2 = EmailAddress.objects.get(pk=self.email2.pk)
        
        self.assertEqual(self.email.reminders_sent, 1)
        self.assertEqual(self.email2.reminders_sent, 1)
        
        self.assertEqual(len(mail.outbox), 1)
    
    def test_send_reminders_timed(self):
        """
        Ensure the time_elapsed argument works as expected
        """
        #no reminders will be sent as not enough time has elapsed
        management.call_command('send_reminders', time_elapsed=600)
        self.assertEqual(len(mail.outbox), 0)
        
        
        
