from datetime import datetime

from django.db import models
from django.forms import ValidationError
from django.contrib.auth.models import User

TOKEN_LENGTH = 12

class SubscriptionManager(models.Manager):
    def create_with_random_token(self, email):
        instance = None

        while instance is None:
            try:
                token = User.objects.make_random_password(length=TOKEN_LENGTH)
                instance = self.create(email=email, token=token)
            except ValidationError:
                continue

        return instance

class Subscription(models.Model):
    email = models.EmailField(unique=True)
    token = models.CharField(null=True, unique=True, max_length=TOKEN_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)

    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True)

    objects = SubscriptionManager()

    def save(self, *args, **kwargs):
        if self.confirmed and self.confirmed_at is None:
            self.confirmed_at = datetime.now()
        super(Subscription, self).save(*args, **kwargs)

