from django.conf import settings
from django.template import RequestContext, Context, loader 
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.views.generic.simple import redirect_to
from django.contrib.sites.models import RequestSite

from nova.models import Subscription

def _send_message(to_addr, subject_template, body_template, context_vars):
    context = Context(context_vars)
    subject = loader.get_template(subject_template).render(context)
    body = loader.get_template(body_template).render(context)
    send_mail(subject, body, settings.DEFAULT_MAIL_FROM, (to_addr,))

def subscribe(request):
    if request.method == 'POST':
        email = request.POST['email']
        subscription = Subscription.objects.create_with_random_token(email)
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
        response = render_to_response('nova/subscribe.html')

    return response

def acknowledge(request):
    subscription = request.session.get('subscription', None)

    if not subscription:
        return redirect_to(request, reverse(subscribe))

    return render_to_response(
        'nova/acknowledge.html', 
        {'email': subscription.email},
        RequestContext(request)
    )


def confirm(request, token):
    subscription = get_object_or_404(Subscription, token=token)
    subscription.confirmed = True
    subscription.save()

    return render_to_response(
        'nova/confirm.html',
        {'email': subscription.email},
        RequestContext(request)
    )
