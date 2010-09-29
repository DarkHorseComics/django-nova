from django.template import RequestContext
from django.http import HttpResponse

from nova.models import Subscription

def subscribe(request):
    return HttpResponse('Hello, {0}'.format(request.POST['email']))

def confirm(request, token=None):
    return HttpResponse('Bad token: {0}'.format(token)) 

