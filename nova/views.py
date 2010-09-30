from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.views.generic.simple import redirect_to

from nova.models import Subscription

def subscribe(request):
    if request.method == 'POST':
        email = request.POST['email']
        subscription = Subscription.objects.create_with_random_token(email)
        request.session['subscription'] = subscription
        response = redirect_to(request, reverse(acknowledge))
    else:
        response = render_to_response('nova/subscribe.html')

    return response

def acknowledge(request):
    subscription = request.session.get('subscription', None)

    if not subscription:
        return redirect_to(request, reverse(subscribe))
    elif not subscription.confirmed:
        send_confirmation_request(subscription)

    return render_to_response(
        'nova/acknowledge.html', 
        {'email': subscription.email},
        RequestContext(request)
    )


def confirm(request, token=None):
    return HttpResponse('Bad token: {0}'.format(token)) 

