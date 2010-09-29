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
    confirmed = models.BooleanField(default=False)
    signup_ts = models.DateTimeField(auto_now_add=True)
    confirm_ts = models.DateTimeField(null=True)

    objects = SubscriptionManager()

