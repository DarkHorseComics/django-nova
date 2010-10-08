"""
Newsletter registration views
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.template import RequestContext, Context, loader 
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.views.generic.simple import redirect_to
from django.contrib.sites.models import RequestSite

from nova.models import Subscription


def _send_message(to_addr, subject_template, body_template, context_vars):
    """
    Helper which generates an email to a single recipient, loading templates
    for the subject line and body.
    """
    context = Context(context_vars)
    # Strip newlines from subject
    subject = loader.get_template(subject_template).render(context).strip()
    body = loader.get_template(body_template).render(context)
    send_mail(subject, body, settings.DEFAULT_MAIL_FROM, (to_addr,))

def subscribe(request):
    """
    Basic signup view
    """
    if request.method == 'POST':
        email = request.POST['email']
        send_email = False

        # Check to see if this email is already subscribed and confirmed
        try:
            # Subscription exists
            subscription = Subscription.objects.get(email=email)
            if subscription.confirmed:
                # Subscription already confirmed
                message = "Thank you! We've previously confirmed your subscription."
                response = render_to_response('nova/error.html',
                                              {'error': message},
                                              RequestContext(request))
            elif (datetime.now() - subscription.created_at) < timedelta(minutes=15):
                # Subscription not confirmed and rate limited
                message = "You've previously submitted a subscription request. Please check %s for your confirmation email or try again in a few minutes." % email
                response = render_to_response('nova/error.html',
                                              {'error': message},
                                              RequestContext(request))
            else:
                # Create new subscription
                subscription.delete()
                ip_addr = request.META.get('REMOTE_ADDR', None)
                subscription = Subscription.objects.create_with_random_token(email, client_addr=ip_addr)
                send_email = True
        except Subscription.DoesNotExist:
            # New subscription
            subscription = Subscription.objects.create_with_random_token(email)
            send_email = True

        if send_email:
            request.session['subscription'] = subscription
            _send_message(
                email, 
                'nova/email/subscribe_subject.txt',
                'nova/email/subscribe_body.txt',
                {
                    'subscription': subscription, 
                    'site': RequestSite(request)
                }
            )
            response = redirect_to(request, reverse(acknowledge))
    else:
        response = render_to_response('nova/subscribe.html', context_instance=RequestContext(request))

    return response

def acknowledge(request):
    """
    Post-signup redirect
    """
    subscription = request.session.get('subscription', None)

    if not subscription:
        return redirect_to(request, reverse(subscribe))

    return render_to_response(
        'nova/acknowledge.html', 
        {'email': subscription.email},
        RequestContext(request)
    )


def confirm(request, token):
    """
    Target view for URLs included in confirmation emails
    """
    subscription = get_object_or_404(Subscription, token=token)
    subscription.confirmed = True
    subscription.save()

    return render_to_response(
        'nova/confirm.html',
        {'email': subscription.email},
        RequestContext(request)
    )
