from django.db import models
from django.contrib.auth.models import User

TOKEN_LENGTH = 12

class SubscriptionManager(models.Manager):
    def create_with_rand_token(self, email):
        instance = None

        while instance is None:
            try:
                token = User.make_random_password(length=TOKEN_LENGTH)
                instance = self.create(email=email, token=token)
            except models.ValidationError:
                continue

class Subscription(models.Model):
    email = models.EmailField()
    token = models.CharField(null=True, unique=True, max_length=TOKEN_LENGTH)
    confirmed = models.BooleanField(default=False)
    signup_ts = models.DateTimeField(auto_now_add=True)
    confirm_ts = models.DateTimeField(null=True)

    objects = SubscriptionManager()

