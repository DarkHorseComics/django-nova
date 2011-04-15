"""
Basic model for a newsletter subscription, minus the newsletter (for now).
More to come...

project specific settings:
NOVA_CONTEXT_PROCESSORS:
    defines a list of functions (similar to django's TEMPLATE_CONTEXT_PROCESSORS) that are called
    when NewsletterIssues render themselves, just before they are sent.  Each function must accept
    the following arguments:
        newsletter_issue: NewsletterIssue instance that is sending the email
        email: EmailAddress instance that is receiving the email
"""
import re
from datetime import datetime
from subprocess import Popen, PIPE
from urllib import urlencode
from urlparse import urlparse

from BeautifulSoup import BeautifulSoup

from django.db import models
from django.forms import ValidationError
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.core.validators import email_re
from django.utils.translation import ugettext_lazy as _
from django.template import Context, Template, TemplateDoesNotExist
from django.template.loader import find_template_loader
from django.contrib.sites.models import Site

TOKEN_LENGTH = 12

def _sanitize_email(email):
    return email.strip().lower()

def _email_is_valid(email):
    return email_re.match(email)

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
        self.email = _sanitize_email(self.email)

        if self.confirmed:
            if self.confirmed_at is None:
                self.confirmed_at = datetime.now()        
            try:
                #set up a user account if it exists
                self.user = User.objects.get(email=self.email)
            except User.DoesNotExist:
                #create one if it doesn't
                #TODO: provide notification to these users, letting them know
                #that they need to reset their password
                username = self._create_unique_username_from_email(self.email)
                self.user = User.objects.create_user(username, self.email)
                self.user.set_unusable_password()
                self.user.save()
            
        super(EmailAddress, self).save(*args, **kwargs)

    @property
    def get_confirm_url(self):
        """
        Returns the unique confirmation URL for this email address,
        suitable for use in follow-up emails.
        """
        return reverse('nova.views.confirm', args=(self.token,))

    def subscribe(self, newsletter):
        """
        Subscribe this email address to a newsletter.
        :return: (Subscription, created)
        """
        return Subscription.objects.get_or_create(email_address=self,
                newsletter=newsletter)

    def unsubscribe(self, newsletter=None):
        """
        Unsubscribe this email address from a specific newsletter.
        If newsletter is None, unsubscribe from all.
        """
        if not newsletter:
            self.subscriptions.all().delete()
        else:
            self.subscriptions.filter(newsletter=newsletter).delete()
            
    def _create_unique_username_from_email(self, email):
        """
        Ensure there are no collisions on user name and
        make certain the username is less than thirty characters long
        """
        unique = False
        #truncate email to thirty characters
        parts = email.split('@')
        username = parts[0][:30]
        
        i = 0
        while not unique:
            #generate a number to append to the end of the username
            i_string = "%s" % i
            try:
                #ensure uniqueness
                user = User.objects.get(username=username)
                
                end = 29 - len(i_string)
                username = "%s%s" % (username[:end], i)
                i += 1
            except User.DoesNotExist:
                unique = True
        return username
    
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
    approvers = models.TextField(null=True, blank=True,
        help_text=_("A whitespace separated list of email addresses."))
    default_template = models.CharField(max_length=255, null=True, blank=True,
        help_text=_("The name of a default template to use for issues of this newsletter."))
    created_at = models.DateTimeField(auto_now_add=True)

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

class PremailerException(Exception):
    """
    Exception thrown when premailer command finishes with a return code other than 0
    """

def send_multipart_mail(subject, txt_body, html_body, from_email, recipient_list,
                        fail_silently=False):
    """
    Sends a multipart email with a plaintext part and an html part.

    :param subject: subject line for email
    :param txt_body: message body for plaintext part of email
    :param html_body: message body for html part of email
    :param from_email: email address from which to send message
    :param recipient_list: list of email addresses to which to send email
    :fail_silently: whether to raise an exception on delivery failure
    """
    message = EmailMultiAlternatives(subject, body=txt_body,
                                     from_email=from_email, to=recipient_list)
    message.attach_alternative(html_body, "text/html")
    return message.send(fail_silently)

def canonicalize_links(html, base_url=None):
    """
    Parse an html string, replacing any relative links with fully qualified links
    """
    if base_url is None:
        base_url = "http://"+Site.objects.get_current().domain
    soup = BeautifulSoup(html)
    relative_links = soup.findAll(href=re.compile('^/'))
    for link in relative_links:
        link['href'] = base_url + link['href']

    return unicode(soup)

def track_links(html, query_string, domain=None):
    """
    Parse an html string and append query_string to all links
    matching the specified domain.
    """
    if not domain:
        domain = Site.objects.get_current().domain

    soup = BeautifulSoup(html)

    for node in soup.findAll('a'):
        href = node['href']
        url = urlparse(href)

        if url.netloc.lstrip('www.') == domain.lstrip('www.'):
            if not url.query:
                href += '?'
            else:
                href += '&'
            href += query_string
            node['href'] = href 
        
    return soup

def get_tracking_string(source, medium, term, campaign):
    """
    Returns a query string for tracking inbound links with Google Analytics.

    :param source: Use to identify a search engine, newsletter name, or other source.
    :param medium: Use to identify a medium such as email or cost-per-click.
    :param term: Use to note keywords for this source.
    :param campaign: Use to identify a sepcific product promotion or campaign.
    """
    args = {
        'utm_source': source,
        'utm_medium': medium,
        'utm_term': term,
        'utm_campaign': campaign,
    }
    return urlencode(args)

class NewsletterIssue(models.Model):
    """
    An issue of a newsletter. This model wraps the actual email subject
    line and template that will be sent out to subscribers.
    """
    newsletter = models.ForeignKey(Newsletter)
    subject = models.CharField(max_length=255, null=False, blank=False)
    template = models.TextField(null=False, blank=True,
        help_text=_("If template is left empty we'll use the default template from the parent newsletter."))
    
    track = models.BooleanField(default=True,
        help_text=_("Add link tracking to all links from this domain."))
    tracking_term = models.CharField(max_length=20, blank=True,
        help_text=_("A short keyword to track by (e.g. 'January')."))
    tracking_campaign = models.CharField(max_length=20, blank=True,
        help_text=_("A short keyword to identify this campaign (e.g. 'DHD')."))

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """
        If template is blank and the parent newsletter has a default
        template, load that default from disk.
        """
        if not self.template:
            if self.newsletter.default_template:
                try:
                    self.template = get_raw_template(self.newsletter.default_template)
                except Exception:
                    pass

        super(NewsletterIssue, self).save(*args, **kwargs)

    def render(self, email, plaintext=False, extra_context=None):
        """
        Render a django template into a formatted newsletter issue.
        uses the setting NOVA_CONTEXT_PROCESSORS to load a list of functions, similar to django's
         template context processors to add extra values to the context dictionary.
        """
        context = Context({
            'issue': self,
            'email': email,
        })

        if extra_context:
            context.update(extra_context)

        for context_processor in getattr(settings, 'NOVA_CONTEXT_PROCESSORS', []):
            module, attr = context_processor.rsplit('.', 1)
            module = __import__(module, fromlist=[attr])
            processor = getattr(module, attr)
            context.update(processor(newsletter_issue=self, email=email))

        # Render template
        template = Template(self.template)
        rendered_template = template.render(context)
        rendered_template = canonicalize_links(rendered_template)

        # Add link tracking
        if self.track:
            tracking_string = get_tracking_string(source=('newsletter-%s' % (self.pk)),
                medium='email',
                term=self.tracking_term,
                campaign=self.tracking_campaign)
            rendered_template = track_links(rendered_template, tracking_string)

        # Run premailer
        rendered_template = self.premail(body_text=rendered_template, plaintext=plaintext)

        return rendered_template

    def premail(self, body_text=None, plaintext=False, base_protocol='http'):
        """
        Run 'premailer' on the specified email body to format html to be readable by email clients
        """
        if body_text is None:
            body_text = self.template
        if not body_text:
            return body_text #nothing to do

        args = ['premailer', '--mode', 'txt' if plaintext else 'html']
        # --base-url currently broken in premailer
        # note: premailer will only return a value in txt mode if the input
        #       contains valid html, head and body tags.
        # todo: either use fixed version of premailer, or re-implement in python

        p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        premailed, err = p.communicate(input=str(body_text))

        if p.returncode != 0:
            raise PremailerException(err)
        else:
            return premailed

    def send(self, render=True, email_addresses=None):
        """
        Sends this issue to subscribers of this newsletter. 
        """
        if not email_addresses:
            email_addresses = self.newsletter.subscribers

        for send_to in email_addresses:
            if render:
                send_multipart_mail(self.subject,
                    txt_body=self.render(send_to, plaintext=True),
                    html_body=self.render(send_to, plaintext=False),
                    from_email=settings.DEFAULT_MAIL_FROM, recipient_list=(send_to.email,)
                )
            else:
                msg = EmailMessage(self.subject, self.template, settings.DEFAULT_MAIL_FROM, (send_to.email,))
                msg.content_subtype = "html"
                msg.send()

    def send_test(self, render=True):
        """
        Sends this issue to an email address specified by an admin user
        """
        email_addresses = []
        approvers = self.newsletter.approvers.split()
        for approver_email in approvers:
            try:
                send_to = EmailAddress.objects.get(email=approver_email.strip(','))
            except EmailAddress.DoesNotExist:
                send_to = EmailAddress.objects.create_with_random_token(email=approver_email.strip(','))

            email_addresses.append(send_to)

        self.send(render, email_addresses)

    def __unicode__(self):
        """
        String-ify this newsletter issue
        """
        return u'%s' % self.subject

    def get_absolute_url(self):
        return reverse('nova.views.preview', args=[self.id])


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
        return u'{email} to {newsletter})'.format(email=self.email_address,
                                                  newsletter=self.newsletter)

def get_raw_template(name, dirs=None):
    """
    Uses Django's template loaders to find and return the
    raw template source. 
    """
    for loader_name in settings.TEMPLATE_LOADERS:
        loader = find_template_loader(loader_name)
        if loader is not None:
            try:
                return loader.load_template_source(name)[0]
            except TemplateDoesNotExist:
                pass
    raise TemplateDoesNotExist(name)
