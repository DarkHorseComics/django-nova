"""
Newsletter registration views
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.template import RequestContext, Context, loader 
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.views.generic.simple import redirect_to
from django.contrib.sites.models import RequestSite

from nova.models import EmailAddress, Subscription, Newsletter, NewsletterIssue, _sanitize_email, _email_is_valid

def _send_message(to_addr, subject_template, body_template, context_vars):
    """
    Helper which generates an email to a single recipient, loading templates
    for the subject line and body.
    """
    context = Context(context_vars)
    # Strip newlines from subject
    subject = loader.get_template(subject_template).render(context).strip()
    body = loader.get_template(body_template).render(context)
    send_mail(subject, body, settings.NOVA_FROM_EMAIL, (to_addr,))

def subscribe(request):
    """
    Basic newsletter signup view
    :todo: Refactor this view to make it more generic.
    """
    context = {}
    template = 'nova/subscribe.html'
    error_template = 'nova/error.html'
    send_email = False 

    if request.method == 'POST':
        email = _sanitize_email(request.POST['email'])
        newsletter_ids = request.POST.getlist('newsletters')

        # Validate email
        if not _email_is_valid(email):
            # Invalid email
            context['error'] = """\
            The email address you submitted was not valid. Please
            try again with a different address."""
            template = error_template
        else:
            # Verify at least one newsletter was submitted
            if len(newsletter_ids) > 0:
                # Get newsletter objects
                newsletters = Newsletter.objects.filter(pk__in=newsletter_ids)

                # Check to see if we've already confirmed this email address
                try:
                    email_address = EmailAddress.objects.get(email=email)

                    if email_address.confirmed:
                        context['error'] = """\
                        We've already confirmed your subscription! Sit back and let
                        the updates roll in."""
                        template = error_template
                    else:
                        if (datetime.now() - email_address.created_at) < timedelta(minutes=15):
                            context['error'] = """\
                                You've previously submitted a subscription request. \
                                Please check %s for your confirmation email \
                                or try again in a few minutes.""" % email_address.email
                            template = error_template 
                        else:
                            # Resend confirmation request
                            # TODO: Don't spam a user with multiple confirmation
                            # requests if possible
                            send_email = True
                    
                except EmailAddress.DoesNotExist:
                    email_address = EmailAddress.objects.create_with_random_token(email)
                    send_email = True

                # Subscribe this email to the selected newsletters
                for newsletter in newsletters: 
                    email_address.subscribe(newsletter)

                if send_email:
                    request.session['email_address'] = email_address
                    _send_message(
                        email_address.email, 
                        'nova/email/subscribe_subject.txt',
                        'nova/email/subscribe_body.txt',
                        {
                            'email_address': email_address, 
                            'site': RequestSite(request)
                        }
                    )
                    return redirect_to(request, reverse(acknowledge))
            else:
                context['error'] = 'You must select at least one newsletter.'
                template = error_template

    else:
        context['newsletters'] = Newsletter.objects.filter(active=True)

    return render_to_response(
        template,
        context,
        RequestContext(request))


def acknowledge(request):
    """
    Post-signup redirect
    """
    email_address = request.session.get('email_address', None)

    if not email_address:
        return redirect_to(request, reverse(subscribe))

    return render_to_response(
        'nova/acknowledge.html',
        {'email': email_address.email},
        RequestContext(request)
    )


def confirm(request, token):
    """
    Target view for URLs included in confirmation emails
    :todo: This is a stub implementation for confirming
    EmailAddresses only, not individual subscriptions. Those
    subscription management views need to be added later.
    """
    email_address = get_object_or_404(EmailAddress, token=token)
    email_address.confirmed = True
    email_address.save()

    return render_to_response(
        'nova/confirm.html',
        {'email': email_address.email},
        RequestContext(request)
    )

def unsubscribe(request, token=None):
    """
    Unsubscribe view
    :todo: Unsubscribe only from indicated newsletters
    """
    template = 'nova/unsubscribe.html'
    email_address = None
    error_msg = None

    if token:
        # Do we have a valid token?
        email_address = get_object_or_404(EmailAddress, token=token)

    if request.method == 'POST':
        if not token:
            try:
                email = _sanitize_email(request.POST.get('email', None))
                email_address = EmailAddress.objects.get(email=email)
            except EmailAddress.DoesNotExist:
                pass
            except EmailAddress.MultipleObjectsReturned:
                pass

            if not email_address:
                error_msg = """\
                Looks like you entered an invalid email address.
                Please try again."""

    # Once we have an email_address, unsubscribe them
    if email_address:
        email_address.unsubscribe()
        template = 'nova/unsubscribe_acknowledge.html'

    context = {
        'error_msg': error_msg,
        'email_address': email_address,
        'token': token,
    }
        
    return render_to_response(
        template,
        context,
        RequestContext(request)
    )

@permission_required('nova.change_newsletterinstance')
def preview(request, newsletter_issue_id):
    """
    Render the specified newsletter issue with a random EmailAddress
    so an admin can preview a newsletter before mailing it.
    """
    email = None
    issue = get_object_or_404(NewsletterIssue, id=newsletter_issue_id)
    subscribers = issue.newsletter.subscribers.order_by('?')

    if subscribers.count() > 0:
        email = subscribers[0]

    premailed_template, _ = issue.premail(track=issue.track, plaintext=False)
    return HttpResponse(issue.render(template=premailed_template, extra_context={'email':email}))
