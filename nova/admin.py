"""
Admin tools for django-nova models
"""

from django import template
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.util import model_ngettext
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

from nova.models import EmailAddress, Newsletter, NewsletterIssue, Subscription

def send_newsletter_issue(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    app_label = opts.app_label

    if request.POST.get('post'):
        # Do send
        for issue in queryset:
            issue.send()

        # Notify user
        n = queryset.count()
        modeladmin.message_user(request,
                _("Successfully sent %(count)d %(newsletters)s.") % {
                        'count': n,
                        'newsletters': model_ngettext(modeladmin.opts, n)
                    })

        # Return None to display the change list page again
        return None

    context = {
        'title': _('Are you sure?'),
        'object_name': force_unicode(opts.verbose_name),
        'queryset': queryset,
        'opts': opts,
        'app_label': app_label,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
    }

    return render_to_response('nova/admin/send_selected_confirmation.html',
            context, context_instance=template.RequestContext(request))

send_newsletter_issue.short_description = _("Send selected to subscribers")

def send_test_newsletter_issue(modeladmin, request, queryset):
    for issue in queryset:
        issue.send_test()

send_test_newsletter_issue.short_description = _("Send selected to approvers")

class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ('email', 'token', 'client_addr', 'confirmed', 'confirmed_at', 'created_at',)
    readonly_fields = ('created_at',)
    list_filter = ('confirmed',)
    search_fields = ['email', 'client_addr',]

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'newsletter', 'created_at', 'active',)
    readonly_fields = ('created_at',)
    list_filter = ('newsletter', 'active',)
    search_fields = ['email_address__email',]

class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('title', 'active', 'created_at', 'approvers',)    
    readonly_fields = ('created_at',)
    list_filter = ('active',)

class NewsletterIssueAdmin(admin.ModelAdmin):
    list_display = ('subject', 'newsletter', 'sent_at','created_at',)
    list_filter = ('newsletter',)
    search_fields = ['subject',]
    readonly_fields = ('rendered_template', 'sent_at',)

    actions = [send_newsletter_issue, send_test_newsletter_issue,]

admin.site.register(EmailAddress, EmailAddressAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(NewsletterIssue, NewsletterIssueAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
