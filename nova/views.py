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

from nova.models import EmailAddress, Subscription, Newsletter

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
    Basic newsletter signup view
    """
    context = {}
    template = 'nova/subscribe.html'
    error_template = 'nova/error.html'
    send_email = False 

    if request.method == 'POST':
        email = request.POST['email']
        newsletter_ids = request.POST.getlist('newsletters')

        # Verify at least one newsletter was submitted
        if len(newsletter_ids) > 0:
            # Get newsletter objects
            newsletters = Newsletter.objects.filter(pk__in=newsletter_ids)

            # Check to see if we've already confirmed this email address
            try:
                email_address = EmailAddress.objects.get(email=email)

                if not email_address.confirmed:
                    if (datetime.now() - email_address.created_at) < timedelta(minutes=15):
                        context['error'] = """\
                            You've previously submitted a subscription request. \
                            Please check %s for your confirmation email \
                            or try again in a few minutes.""" % email_address.email
                        template = template_error
                    else:
                        email_address.delete()
                        ip_addr = request.META.get('REMOTE_ADDR', None)
                        email_address = EmailAddress.objects.create_with_random_token(email, client_addr=ip_addr)
                        send_email = True
                
            except EmailAddress.DoesNotExist:
                email_address = EmailAddress.objects.create_with_random_token(email)
                send_email = True

            # Subscribe this email to the selected newsletters
            for newsletter in newsletters: 
                try:
                    Subscription.objects.get(email_address=email_address,
                                             newsletter=newsletter)
                except Subscription.DoesNotExist:
                    Subscription.objects.create(email_address=email_address,
                                                newsletter=newsletter)

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
    """
    email_address = get_object_or_404(EmailAddress, token=token)
    email_address.confirmed = True
    email_address.save()

    return render_to_response(
        'nova/confirm.html',
        {'email': email_address.email},
        RequestContext(request)
    )

def unsubscribe(request, token):
    """
    Unsubscribe view
    :todo: Unsubscribe only from specified subscriptions
    """
    email_address = get_object_or_404(EmailAddress, token=token)
    template = 'nova/unsubscribe.html'

    if request.method == 'POST':
        Subscription.objects.filter(email_address=email_address).delete()
        template = 'nova/unsubscribe_acknowledge.html'

    context = {
        'email': email_address.email,
        'token': token,
    }
        
    return render_to_response(
        template,
        context,
        RequestContext(request)
    )
