from django.utils import timezone
from rest_framework import serializers

from api.models import ScheduledEmailNotification


class ScheduledEmailNotificationSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ScheduledEmailNotification
        fields = [
            "id",
            "recipient_email",
            "scheduled_at",
            "message",
            "sent_at",
            "created_at",
        ]
        read_only_fields = ["id", "recipient_email", "sent_at", "created_at"]

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Escolha um horário futuro.")
        return value

    def validate_message(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Escreva uma mensagem.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        if not request.user.email:
            raise serializers.ValidationError(
                {"recipient_email": "Cadastre um e-mail na sua conta para agendar notificações."}
            )
        return ScheduledEmailNotification.objects.create(user=request.user, **validated_data)
