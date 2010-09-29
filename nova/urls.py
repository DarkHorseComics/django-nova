from django.conf.urls.defaults import patterns, include, handler404, handler500

urlpatterns = patterns('nova.views',
    (r'subscribe/', 'subscribe'),
    (r'confirm/', 'confirm'),
    (r'confirm/(?P<token_id>\w+)/', 'confirm'),
)

