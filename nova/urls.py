from django.conf.urls.defaults import patterns, include, handler404, handler500

urlpatterns = patterns('nova.views',
    (r'subscribe/', 'subscribe'),
    (r'acknowledge/', 'acknowledge'),
    (r'confirm/(?P<token>\w+)/', 'confirm'),
)

