"""
Default URL patterns for the newsletter signup views
"""
from django.conf.urls.defaults import patterns, include, handler404, handler500

urlpatterns = patterns('nova.views',
    (r'unsubscribe/(?P<token>\w+)/', 'unsubscribe'),
    (r'subscribe/', 'subscribe'),
    (r'acknowledge/', 'acknowledge'),
    (r'confirm/(?P<token>\w+)/', 'confirm'),
)

