"""
Default URL patterns for the newsletter signup views
"""
from django.conf.urls.defaults import patterns, include, handler404, handler500

urlpatterns = patterns('nova.views',
    (r'unsubscribe/(?P<token>\w+)/', 'unsubscribe'),
    (r'unsubscribe/', 'unsubscribe'),
    (r'subscribe/', 'subscribe'),
    (r'update_subscriptions/', 'update_subscriptions'),
    (r'acknowledge/', 'acknowledge'),
    (r'confirm/(?P<token>\w+)/', 'confirm'),
    (r'preview/(?P<newsletter_issue_id>\d+)/', 'preview')
)

