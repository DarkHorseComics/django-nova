"""
Some helper functions for django-nova.
"""
import re
import string

from urllib import urlencode
from urlparse import urlparse

from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives

from BeautifulSoup import BeautifulSoup

class PremailerException(Exception):
    """
    Exception thrown when premailer command finishes with a return code other than 0
    """

def send_multipart_mail(subject, txt_body, html_body, from_email, recipient_list,
                        headers=None, fail_silently=False):
    """
    Sends a multipart email with a plaintext part and an html part.

    :param subject: subject line for email
    :param txt_body: message body for plaintext part of email
    :param html_body: message body for html part of email
    :param from_email: email address from which to send message
    :param recipient_list: list of email addresses to which to send email
    :param fail_silently: whether to raise an exception on delivery failure
    """
    message = EmailMultiAlternatives(subject, body=txt_body,
                                     from_email=from_email, to=recipient_list, headers=headers)

    message.attach_alternative(html_body, "text/html")
    return message.send(fail_silently)

def canonicalize_links(html, base_url=None):
    """
    Parse an html string and replace any relative links with fully qualified links.
    :param html: The document to canonicalize.
    :param base_url: The (optional) base url to canonicalize to.
    """
    if base_url is None:
        base_url = "http://"+Site.objects.get_current().domain

    soup = BeautifulSoup(html)
    relative_links = soup.findAll(href=re.compile('^/'))

    for link in relative_links:
        link['href'] = base_url + link['href']

    return unicode(soup)

def get_anchor_text(anchor):
    """
    Tries to get the anchor text of an html link, or the alt text attribute
    of an image within a link.
    :param anchor: A BeautifulSoup node representing an HTML anchor tag.
    """
    alttext = anchor.string

    if not alttext:
        # Does this anchor contain child nodes?
        children = anchor.contents
        if len(children) > 0:
            # Check the first child to see if it is an image tag
            first_child = children[0]
            if first_child.name == 'img':

                if first_child.has_key('alt'):
                    # Get the image alt text
                    alttext = first_child['alt']
                else:
                    # If the alt attribute is empty, return default
                    alttext = 'image'
            else:
                alttext = 'html'

    return alttext

TRACKED_LINK_CLASS = 'tracked'

def track_document(html, domain=None, campaign=None, source='newsletter', medium='email'):
    """
    Loops over a bundle of HTML and tracks any links contained therein.

    :param html: An HTML string that will be parsed for links.
    :param domain: A string representation of the domain for which links should be tracked.
    :param campaign: Use to identify a sepcific product promotion or campaign.
    :param source: Use to identify a search engine, newsletter name, or other source.
    :param medium: Use to identify a medium such as email or cost-per-click.

    :return: The tracked document is returned as a unicode string.
    """
    soup = BeautifulSoup(html)
    anchors = soup.findAll('a')

    if not domain:
        domain = Site.objects.get_current().domain

    tracking_args = {
        'utm_campaign': campaign,
        'utm_source': source,
        'utm_medium': medium,
        'utm_term': None,
    }

    # Loop over all anchor tags in the document
    for index, anchor in enumerate(anchors):
        anchor_css_class = anchor.get('class', '')
        
        # Skip links that have already been tracked
        if TRACKED_LINK_CLASS not in anchor_css_class:
            url = anchor['href']
            parsed_url = urlparse(url)

            # Only track links from specific domains
            # :todo: Make this comparison less stupid
            if domain in parsed_url.netloc:
                # Append appropriate query prefix to url
                if not parsed_url.query:
                    url += '?'
                else:
                    url += '&'

                # Generate term that is unique per anchor and include alttext for readability
                tracking_args['utm_term'] = '{source}-{index}-{alttext}'.format(source=source,
                        index='link-%s' % (index+1,), alttext=get_anchor_text(anchor))
                url += urlencode(tracking_args)

                # Update href and flag anchor as tracked
                anchor['href'] = url
                anchor['class'] = string.strip("%s %s" % (anchor_css_class, TRACKED_LINK_CLASS))

    return unicode(soup)
