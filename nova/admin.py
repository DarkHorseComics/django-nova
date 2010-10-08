"""
Admin tools for django-nova models
"""

from django.contrib import admin

from nova.models import Subscription

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'token', 'created_at', 'client_addr', 'confirmed', 'confirmed_at')
    readonly_fields = ('created_at',)
    list_filter = ('confirmed',)

admin.site.register(Subscription, SubscriptionAdmin)

