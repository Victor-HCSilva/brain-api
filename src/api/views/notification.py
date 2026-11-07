from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from api.models import ScheduledEmailNotification
from api.serializers.notification import ScheduledEmailNotificationSerializer


class ScheduledEmailNotificationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ScheduledEmailNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return ScheduledEmailNotification.objects.none()
        return ScheduledEmailNotification.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
