from django.db import models


class Activable(models.Model):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class TimeStamp(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivableAndTimeStamp(TimeStamp, Activable):
    class Meta:
        abstract = True
