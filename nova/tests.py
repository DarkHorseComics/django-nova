"""
Basic unit and functional tests for newsletter signups
"""
from datetime import datetime

from django.test import TestCase
from django.core import mail, management
from django.core.urlresolvers import reverse
from django.conf import settings
from django.template import Template, Context
from django.template.loader import render_to_string

from nova.models import EmailAddress, Subscription, Newsletter, NewsletterIssue, send_multipart_mail

def _make_newsletter(title):
    return Newsletter.objects.create(title=title)

def _make_email(email):
    return EmailAddress.objects.create_with_random_token(email)

def _make_subscription(email_address, newsletter):
    return Subscription.objects.create(email_address=email_address,
                                       newsletter=newsletter)

class TestUtilites(TestCase):
    """
    Test utility functions defined for Nova
    """

    def test_send_multipart(self):
        """
        Verify that the send_multipart_mail function actually sends multipart emails
        """
        subject = "test subject"
        txt_body = "plaintext email"
        html_body = "<html><body><p>html message</p></body></html>"
        from_email = "from@testing.darkhorse.com"
        recipient_list = ["to@testing.darkhorse.com"]

        send_multipart_mail(subject, txt_body, html_body, from_email, recipient_list)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertEqual(subject, message.subject)
        self.assertEqual(txt_body, message.body)
        self.assertEqual((html_body, 'text/html'), message.alternatives[0])

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

    def test_auto_signup_user(self):
        """
        Check Users are auto-assigned
        """
        email = _make_email('test@example.com')
        email.confirmed = True
        email.save()
        email = EmailAddress.objects.get(pk=email.pk)
        self.assertTrue(email.user is not None)

    def test_subscribe(self):
        """
        Verify that an email address can be subscribed to
        a newsletter.
        """
        email = _make_email('test_subscribe@example.com')
        newsletter = _make_newsletter("Test Newsletter")
        newsletter2 = _make_newsletter("Test Newsletter 2")

        # Sanity check
        self.assertEqual(Subscription.objects.filter(email_address=email).count(), 0)

        # Subscribe this email to the newsletter
        subscription, created = email.subscribe(newsletter)

        # Verify a subscription was created
        self.assertTrue(created)

        # Verify the subscription was created for the correct newsletter
        self.assertEqual(newsletter, subscription.newsletter)

        # Verify a new subscription exists for this user
        self.assertEqual(Subscription.objects.filter(email_address=email).count(), 1)
        


    def test_unsubscribe(self):
        """
        Verify that a user can be successfully unsubscribed from
        a newsletter.
        """
        email = _make_email('test_unsub1@example.com')
        newsletter = _make_newsletter("Test Newsletter")
        newsletter2 = _make_newsletter("Test Newsletter 2")

        # Subscribe email to newsletter
        subscription, created = email.subscribe(newsletter)

        # Verify subscription
        self.assertTrue(created)
        self.assertEqual(newsletter, subscription.newsletter)
        self.assertEqual(Subscription.objects.filter(email_address=email).count(), 1)

        # Subscribe email to another newsletter
        subscription, created = email.subscribe(newsletter2)

        # Verify second subscription
        self.assertTrue(created)
        self.assertEqual(newsletter2, subscription.newsletter)
        self.assertEqual(Subscription.objects.filter(email_address=email).count(), 2)

        # Unsubscribe email
        email.unsubscribe()

        # Verify all subscriptions have been removed
        self.assertEqual(Subscription.objects.filter(email_address=email).count(), 0)

    def test_unsubscribe_newsletter(self):
        """
        Verify that a user can unsubscribe from a specific newsletter
        without nuking all of their subscriptions.
        """
        email = _make_email('test_unsub2@example.com')
        newsletter = _make_newsletter("Test Newsletter")
        newsletter2 = _make_newsletter("Test Newsletter 2")

        # Subscribe email to newsletter
        subscription, created = email.subscribe(newsletter)

        # Verify subscription
        self.assertTrue(created)
        self.assertEqual(newsletter, subscription.newsletter)
        self.assertEqual(Subscription.objects.filter(email_address=email).count(), 1)

        # Subscribe email to another newsletter
        subscription, created = email.subscribe(newsletter2)

        # Verify second subscription
        self.assertTrue(created)
        self.assertEqual(newsletter2, subscription.newsletter)
        self.assertEqual(Subscription.objects.filter(email_address=email).count(), 2)

        # Unsubscribe email from first newsletter
        email.unsubscribe(newsletter)

        # Verify only the first subscription was removed
        subscriptions = Subscription.objects.filter(email_address=email)
        self.assertEqual(subscriptions.count(), 1)
        self.assertEqual(subscriptions[0].newsletter, newsletter2)

def test_context_processor(newsletter_issue):
    """
    nova context processor for testing.
    """
    if not newsletter_issue:
        return {'test': 'error! got newsletter_issue:{0}'.format(newsletter_issue)}
    else:
        return {'test': 'extra test context'}

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

        self.template = "<html><head></head><body><h1>Test</h1></body></html>"

        self.plaintext = "****\nTest\n****"

        # Create an issue for each newsletter
        self.newsletter_issue1 = NewsletterIssue()
        self.newsletter_issue1.subject = 'Test Newsletter Issue 1'
        self.newsletter_issue1.template = self.template
        self.newsletter_issue1.newsletter = self.newsletter1
        self.newsletter_issue1.save()

        self.newsletter_issue2 = NewsletterIssue()
        self.newsletter_issue2.subject = 'Test Newsletter Issue 2'
        self.newsletter_issue2.template = self.template
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

    def test_default_template(self):
        """
        Verify that on save a NewsletterIssue is assigned
        a default template from the parent Newsletter.
        """
        template_name = 'nova/test.html'
        self.newsletter1.default_template = template_name
        self.newsletter1.save()

        # Sanity check
        self.assertEqual(self.newsletter1.default_template, template_name)

        issue = NewsletterIssue()
        issue.subject = 'Test'
        issue.newsletter = self.newsletter1
        issue.save()

        self.assertTrue(issue.template is not None)

        context = Context({})
        expected_template = render_to_string(template_name, context)
        issue_template = Template(issue.template).render(context)
        self.assertEqual(expected_template, issue_template)

        # Verify an existing template is not overwritten
        new_template = 'hai'
        issue.template = new_template
        issue.save()
        self.assertEqual(new_template,
            NewsletterIssue.objects.get(pk=issue.pk).template)

    def test_render(self):
        """
        Verify that the NewsletterIssue template is correctly
        rendered.
        """
        email = 'test@example.com'

        template = """\
        Issue ID: {{ issue.pk }}
        Date: {% now "Y-m-d" %}
        Email: {{ email }}"""
        
        issue = NewsletterIssue()
        issue.subject = 'Test'
        issue.template = template
        issue.newsletter = self.newsletter1
        issue.save()

        expected_template = """\
        Issue ID: {issue_id}
        Date: {date:%Y-%m-%d}
        Email: {email}""".format(issue_id=issue.pk, date=datetime.now(), email=email)

        rendered_template = issue.render(extra_context={
            'email': email})
        self.assertEqual(rendered_template, expected_template)

    def test_nova_context_processors(self):
        """
        Verify that NewsletterIssues use NOVA_CONTEXT_PROCESSORS to render themselves when
        render() is called
        """
        old_settings = getattr(settings, 'NOVA_CONTEXT_PROCESSORS', '!unset')
        settings.NOVA_CONTEXT_PROCESSORS = ['nova.tests.test_context_processor']

        try:
            issue = NewsletterIssue(template="{{ test }}")
            issue.newsletter = self.newsletter1
            issue.save()

            self.assertEqual('extra test context', issue.render(extra_context={
                'email': EmailAddress(email='foo@example.com')}))
        finally:
            if old_settings == '!unset':
                del settings.NOVA_CONTEXT_PROCESSORS
            else:
                settings.NOVA_CONTEXT_PROCESSORS = old_settings

    def test_link_canonicalization(self):
        """
        Ensure that links are canonicalized correctly.
        """
        template = """\
        <a href="/">Home</a>
        <a href="/store">Store</a>
        <a href="http://www.google.com/">Fully Qualified</a>"""

        issue = NewsletterIssue()
        issue.subject = 'Test'
        issue.template = template
        issue.newsletter = self.newsletter1
        issue.save()

        rendered_template = issue.render(track=False, premail=False)

        canon1 = '<a href="http://example.com/">Home</a>'
        canon2 = '<a href="http://example.com/store">Store</a>'

        self.assertTrue(canon1 in rendered_template)
        self.assertTrue(canon2 in rendered_template)

        ignore1 = '<a href="http://www.google.com/">Fully Qualified</a>'

        self.assertTrue(ignore1 in rendered_template)

    def test_link_tracking(self):
        """
        Verify link tracking works as expected.
        """
        template = """\
        <html>
            <head>
                <style>
                    a {
                        font-weight: bold;
                        color: pink;
                    }
                </style>
            </head>
            <body>
                <a href="http://www.example.com/">Google</a>
                <a href="http://www.darkhorse.com/?hai=true">Dark Horse</a>
                <a href="http://digital.darkhorse.com/">Digital Dark Horse</a>
                <a href="http://www.tfaw.com/">TFAW</a>
            </body>
        </html>
        """
        
        issue = NewsletterIssue()
        issue.subject = 'Test'
        issue.template = template
        issue.newsletter = self.newsletter1
        issue.tracking_campaign = 'DHD'
        issue.tracking_domain = 'darkhorse.com'
        issue.save()

        track1 = """<a href="http://www.darkhorse.com/?hai=true&amp;utm_campaign=DHD&amp;utm_medium=email&amp;utm_source=newsletter-{pk}&amp;utm_term=newsletter-{pk}-link-1-Dark+Horse" class="tracked">Dark Horse</a>""".format(pk=issue.newsletter.pk)

        track2 = """<a href="http://digital.darkhorse.com/?utm_campaign=DHD&amp;utm_medium=email&amp;utm_source=newsletter-{pk}&amp;utm_term=newsletter-{pk}-link-2-Digital+Dark+Horse" class="tracked">Digital Dark Horse</a>""".format(pk=issue.newsletter.pk)
        
        rendered_template = issue.render(premail=False)

        # Assert both darkhorse.com links were tracked
        self.assertTrue(track1 in rendered_template)
        self.assertTrue(track2 in rendered_template)

        # Assert that only two links were tracked
        self.assertEqual(rendered_template.count('tracked'), 2)

    def test_premail(self):
        """
        Verify that the premail method on NewsletterItems correctly formats the given html
        """
        pre_html = """\
        <html>
        <head>
        <style>
        .foo {
            color: red;
        }
        </style>
        </head>
        <body>
        <p class="foo">Some Text</p>
        </body>
        </html>
        """

        expected_html = """\
        <html>
        <head>
        
        </head>
        <body>
        <p class="foo" style="color: red;">Some Text</p>
        </body>
        </html>
        """

        issue = NewsletterIssue(template=pre_html)

        self.assertEqual(expected_html, issue.premail())
    
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
            self.assertEqual(message.body, self.plaintext)
            self.assertEqual(message.alternatives[0][1], 'text/html')
            self.assertEqual(message.alternatives[0][0], self.newsletter_issue1.template)

    def test_send(self):
        """
        Ensure that a newsletter issue is successfully sent
        to all *confirmed* subscribers of that newsletter.
        """
        self.assertEqual(self.newsletter1.subscribers.count(), 3)

        self.newsletter_issue1.send()

        self.assertEqual(len(mail.outbox), 3)

        for message in mail.outbox:
            self.assertNotEqual(self.unconfirmed_email.email, message.to[0])
            self.assertNotEqual(self.exclude_email.email, message.to[0])
            self.assertEqual(message.subject, self.newsletter_issue1.subject)
            self.assertEqual(message.body, self.plaintext)
            self.assertEqual(message.alternatives[0][1], 'text/html')
            self.assertEqual(message.alternatives[0][0], self.newsletter_issue1.template)

    def test_send_custom_list(self):
        """
        Ensure that a newsletter issue is successfully sent to
        a custom list of recipients.
        """
        emails = ['test@example.com', 'test2@example.net']
        email_addresses = []
        for email in emails:
            e = EmailAddress.objects.create(email=email)
            email_addresses.append(e)
            
        # Sanity Check
        self.assertEqual(len(email_addresses), 2)
        self.assertEqual(self.newsletter1.subscribers.count(), 3)

        self.newsletter_issue1.send(email_addresses=email_addresses)

        self.assertEqual(len(mail.outbox), 2)

        subscribers = [email.email for email in self.newsletter1.subscribers]

        for message in mail.outbox:
            self.assertTrue(message.to[0] not in subscribers)
            self.assertNotEqual(self.unconfirmed_email.email, message.to[0])
            self.assertNotEqual(self.exclude_email.email, message.to[0])
            self.assertEqual(message.subject, self.newsletter_issue1.subject)
            self.assertEqual(message.body, self.plaintext)
            self.assertEqual(message.alternatives[0][1], 'text/html')
            self.assertEqual(message.alternatives[0][0], self.newsletter_issue1.template)

    def test_send_unsubscribe(self):
        """
        Verify that a subscriber who once received issues, can
        successfully opt-out by unsubscribing.
        """
        newsletter_issue = self.newsletter_issue1
        email_address = newsletter_issue.newsletter.subscribers[0]

        # Unsubscribe email
        email_address.unsubscribe()

        # Verify unsubscribe
        self.assertTrue(email_address not in newsletter_issue.newsletter.subscribers)

        # Verify unsubscribed email not in sent issues
        newsletter_issue.send()

        for message in mail.outbox:
            self.assertNotEqual(email_address.email, message.to[0])


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

        self.assertEqual(confirm_url, email_address.get_confirm_url())

        message = mail.outbox[0].body
        self.assertTrue(confirm_url in message)
        
        response = self.client.get(confirm_url)
        self.assertTrue(email in response.content)

        email_address = EmailAddress.objects.get(pk=email_address.pk)
        self.assertTrue(email_address.confirmed)

    def test_unsubscribe(self):
        """
        Test that a user can unsubscribe using a token.
        """
        # Create subscription
        email = 'test_confirm@example.com'
        self._do_subscribe(email=email, newsletters=(self.newsletter1.pk,
                                                     self.newsletter2.pk,))
        other_email = 'other@example.com'
        self._do_subscribe(email=other_email, newsletters=(self.newsletter1.pk,
                                                           self.newsletter2.pk,))

        # Confirm email addresses
        for email_address in EmailAddress.objects.all():
            confirm_url = reverse('nova.views.confirm', args=(email_address.token,))
            self.client.get(confirm_url)

        # Assert we have 2 confirmed email addresses
        self.assertEqual(EmailAddress.objects.filter(confirmed=True).count(), 2)

        # Assert emails have the correct number of subscriptions
        for email_address in EmailAddress.objects.all():
            self.assertEqual(Subscription.objects.filter(email_address=email_address, active=True).count(), 2)

        # Test unsubscribing with a token
        email_address = EmailAddress.objects.get(email=email)
        unsubscribe_url = reverse('nova.views.unsubscribe', args=(email_address.token,))
        response = self.client.get(unsubscribe_url)

        self.assertEqual(unsubscribe_url, email_address.get_unsubscribe_url())

        # Ensure this user was successfully unsubscribed
        response = self.client.post(unsubscribe_url)
        self.assertEqual(Subscription.objects.filter(email_address=email_address).count(), 0)

        # Make sure other address is still subscribed
        other_email_address = EmailAddress.objects.get(email=other_email)
        self.assertEqual(Subscription.objects.filter(email_address=other_email_address, active=True).count(), 2)

    def test_unsubscribe_email(self):
        """
        Test that a user can unsubscribe using only their email address.
        """
        # Create subscription
        email = 'bob@example.com'
        self._do_subscribe(email=email, newsletters=(self.newsletter1.pk,
                                                     self.newsletter2.pk,))
        other_email = 'alice@example.com'
        self._do_subscribe(email=other_email, newsletters=(self.newsletter1.pk,
                                                           self.newsletter2.pk,))

        # Confirm email addresses
        for email_address in EmailAddress.objects.all():
            confirm_url = reverse('nova.views.confirm', args=(email_address.token,))
            self.client.get(confirm_url)

        # Assert we have 2 confirmed email addresses
        self.assertEqual(EmailAddress.objects.filter(confirmed=True).count(), 2)

        # Assert emails have the correct number of subscriptions
        for email_address in EmailAddress.objects.all():
            self.assertEqual(Subscription.objects.filter(email_address=email_address, active=True).count(), 2)

        # Test unsubscribe view
        email_address = EmailAddress.objects.get(email=email)
        unsubscribe_url = reverse('nova.views.unsubscribe')
        response = self.client.get(unsubscribe_url)

        # Test unsubscribe
        response = self.client.post(unsubscribe_url, {'email': email_address.email})
        self.assertEqual(Subscription.objects.filter(email_address=email_address).count(), 0)

        # Make sure other address is still subscribed
        other_email_address = EmailAddress.objects.get(email=other_email)
        self.assertEqual(Subscription.objects.filter(email_address=other_email_address, active=True).count(), 2)
        

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
        
        #remind all, no matter when they signed up
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
        management.call_command('send_reminders', days_elapsed=1)
        self.assertEqual(len(mail.outbox), 0)
        
        
        
