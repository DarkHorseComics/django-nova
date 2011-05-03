from django import forms
from django.utils.translation import ugettext_lazy as _

from nova.models import EmailAddress, Newsletter, _sanitize_email, _email_is_valid
from html5.forms.widgets import EmailInput

class NovaSubscribeForm(forms.Form):
    """
    A simple form to subscribe a user to a set of newsletters.
    """
    email_address = forms.EmailField(label=_('Email Address'),
        widget=EmailInput(attrs={'placeholder': _('Email Address')}))
    newsletters = forms.ModelMultipleChoiceField(label=_('Newsletters'),
            queryset=Newsletter.objects.filter(active=True),
            widget=forms.CheckboxSelectMultiple)

    def clean_email_address(self):
        """
        Use our utility methods to sanitize and validate the submitted email address.
        """
        email = _sanitize_email(self.cleaned_data['email_address'])
        if not _email_is_valid(email):
            raise forms.ValidationError(_('The email address you submitted was not valid.'))

        return email

    def save(self):
        """
        Create an EmailAddress object for this email and
        subscribe to the selected newsletters.
        """
        email = self.cleaned_data['email_address']
        newsletters = self.cleaned_data['newsletters']

        try:
            email_address = EmailAddress.objects.get(email=email)
        except EmailAddress.DoesNotExist:
            email_address = EmailAddress.objects.create_with_random_token(email)

        # Subscribe this email to the selected newsletters
        for newsletter in newsletters:
            email_address.subscribe(newsletter)

        return email_address


class NovaUnsubscribeForm(forms.Form):
    """
    A simple form that accepts an email address
    to unsubscribe from all active subscriptions.
    """
    email_address = forms.EmailField(label=_('Email Address'),
        widget=EmailInput(attrs={'placeholder': _('Email Address')}))

    def __init__(self, *args, **kwargs):
        super(NovaUnsubscribeForm, self).__init__(*args, **kwargs)
        self.email_address = None
    
    def clean_email_address(self):
        """
        Use our utility methods to sanitize and validate the submitted email address.
        """
        email = _sanitize_email(self.cleaned_data['email_address'])
        if not _email_is_valid(email):
            raise forms.ValidationError(_('The email address you submitted was not valid.'))

        try:
            self.email_address = EmailAddress.objects.get(email=email)
            if self.email_address.subscriptions.count() < 1:
                raise forms.ValidationError(_('This email has no active subscriptions.'))
        except EmailAddress.DoesNotExist:
            raise forms.ValidationError(_('The email address you submitted does not exist in our system.'))

        return email

    def save(self):
        """
        If this EmailAddress exists, unsubscribe them from all
        active subscriptions.
        """
        if self.email_address:
            self.email_address.unsubscribe()

        return self.email_address


class SubscriptionForm(forms.Form):
    """
    Form to add / remove subscriptions for a specific user / email address
    """
    email_address = forms.CharField()
    newsletters = forms.ModelMultipleChoiceField(queryset=Newsletter.objects.filter(active=True),
                                                 widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, data=None, user=None, *args, **kwargs):
        """
        If a user is specified, use that user's email address (and change email_address to a hidden field)
        """
        if data is not None:
            kwargs['data'] = data
        super(SubscriptionForm, self).__init__(*args, **kwargs)

        if user and user.is_authenticated():
            self.user = user
            self.fields['email_address'].initial = self.user.email
            self.fields['email_address'].widget = forms.HiddenInput()

            newsletters = self.fields['newsletters'].queryset
            self.fields['newsletters'].initial = [n.id for n in newsletters.filter(subscription__email_address__user=self.user)]
        else:
            self.user = None

    def clean_email_address(self):
        """
        use our utility methods to sanitize & verify email address
        """
        email = _sanitize_email(self.cleaned_data['email_address'])
        if not _email_is_valid(email):
            raise forms.ValidationError("The email address you submitted was not valid."
                                        "Please try again with a different address.")
        return email

    def save(self):
        """
        Create an EmailAddress object if one hasn't been created yet, subscribe to selected newsletters, and
        unsubscribe from deselected newsletters
        """
        email = self.cleaned_data['email_address']
        newsletters = self.cleaned_data['newsletters']

        # Check to see if we've already confirmed this email address
        try:
            email_address = EmailAddress.objects.get(email=email)
        except EmailAddress.DoesNotExist:
            email_address = EmailAddress.objects.create_with_random_token(email)
        if self.user and email_address.user != self.user:
            email_address.user = self.user
            email_address.save()

        # Subscribe this email to the selected newsletters
        for newsletter in newsletters:
            email_address.subscribe(newsletter)

        # Unsubscribe from deselected newsletters
        deselected_newsletters = self.fields['newsletters'].queryset.exclude(id__in=newsletters)
        for newsletter in deselected_newsletters:
            email_address.unsubscribe(newsletter)
