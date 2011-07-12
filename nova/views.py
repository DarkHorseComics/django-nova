"""
Newsletter registration views
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.http import HttpResponse
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.sites.models import RequestSite
from django.contrib.auth.decorators import permission_required
from django.views.generic.simple import redirect_to
from django.template import RequestContext, Context, loader 
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext_lazy as _

from nova.models import EmailAddress, Subscription, Newsletter, NewsletterIssue, _sanitize_email, _email_is_valid
from nova.forms import NovaSubscribeForm, NovaUnsubscribeForm, SubscriptionForm

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

def update_subscriptions(request, template_name='nova/subscribe.html', redirect_url=None, extra_context=None):
    """
    View that allows existing users (or even new users) to modify their subscriptions
    """
    if request.method == "POST":
        form = SubscriptionForm(data=request.POST, user=request.user)
        if form.is_valid():
            form.save()
            return redirect_to(request, redirect_url)
    else:
        form = SubscriptionForm(user=request.user)

    context = {
        'form': form
    }
    if extra_context:
        context.update(extra_context)
    return render_to_response(template_name, context, RequestContext(request))
    

def subscribe(request, redirect_url=None, send_confirm_email=True, template_name='nova/subscribe.html'):
    """
    Basic subscribe view that registers a user with
    a newsletter and sends them a confirmation email.
    """
    if not redirect_url:
        redirect_url = reverse('nova.views.acknowledge')

    if request.method == 'POST':
        form = NovaSubscribeForm(data=request.POST)

        if form.is_valid():
            email_address = form.save()
            request.session['email_address'] = email_address

            # Send a confirmation email
            if not email_address.confirmed:
                if send_confirm_email:
                    _send_message(
                        email_address.email, 
                        'nova/email/subscribe_subject.txt',
                        'nova/email/subscribe_body.txt',
                        {
                            'email_address': email_address,
                            'site': RequestSite(request)
                        }
                    )

            return redirect_to(request, redirect_url)
    else:
        form = NovaSubscribeForm()

    context = {
        'form': form,
    }

    return render_to_response(template_name, context, RequestContext(request))

def confirm(request, token, template_name='nova/confirm.html'):
    """
    Target view for URLs included in confirmation emails
    :todo: This is a stub implementation for confirming
    EmailAddresses only, not individual subscriptions. Those
    subscription management views need to be added later.
    """
    email_address = None

    try:
        email_address = EmailAddress.objects.get(token=token)
        email_address.confirmed = True
        email_address.save()
    except:
        messages.add_message(request, messages.ERROR,
                _('The token you submitted was invalid.'))
        return redirect_to(request, reverse('nova.views.subscribe'))

    return render_to_response(template_name,
        {'email': email_address.email}, RequestContext(request))

def unsubscribe(request, template_name='nova/unsubscribe.html'):
    """
    Simple view to unsubscribe an EmailAddress
    from all active Subscriptions.
    """
    email_address = None

    if request.method == 'POST':
        form = NovaUnsubscribeForm(data=request.POST)

        if form.is_valid():
            # The form handles unsubscribing the email
            email_address = form.save()
            request.session['email_address'] = email_address
            return redirect_to(request, reverse('nova.views.acknowledge_unsubscribe'))
    else:
        form = NovaUnsubscribeForm()

    context = {
        'form': form,
    }
        
    return render_to_response(template_name, context, RequestContext(request))

def unsubscribe_with_token(request, token=None):
    """
    Unsubscribe an EmailAddress with a token
    """
    email_address = None

    if token:
        try:
            email_address = EmailAddress.objects.get(token=token)
            email_address.unsubscribe()
            request.session['email_address'] = email_address
            return redirect_to(request, reverse('nova.views.acknowledge_unsubscribe'))
        except:
            messages.add_message(request, messages.ERROR,
                    _('The token you submitted was invalid.'))

    return redirect_to(request, reverse('nova.views.unsubscribe'))

def acknowledge(request, template_name='nova/acknowledge.html'):
    """
    Post-signup redirect
    """
    email_address = request.session.get('email_address', None)

    if not email_address:
        return redirect_to(request, reverse('nova.views.subscribe'))

    return render_to_response(template_name,
            {'email_address': email_address}, RequestContext(request))

def acknowledge_unsubscribe(request, template_name='nova/acknowledge_unsubscribe.html'):
    """
    Post-unsubscribe redirect
    """
    email_address = request.session.get('email_address', None)

    if not email_address:
        return redirect_to(request, reverse('nova.views.unsubscribe'))

    return render_to_response(template_name,
            {'email_address': email_address}, RequestContext(request))

@permission_required('nova.change_newsletterissue')
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

    premailed_template, _ = issue.premail(track=issue.track, plaintext=False,
            template=issue.render())
    return HttpResponse(premailed_template)
