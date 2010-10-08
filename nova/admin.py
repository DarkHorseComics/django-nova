"""
Admin tools for django-nova models
"""

from django.contrib import admin

from nova.models import Subscription

class SubscriptionAdmin(admin.ModelAdmin):
    fields = ('email', 'token', 'confirmed')
    list_filter = ('confirmed',)

admin.site.register(Subscription, SubscriptionAdmin)

