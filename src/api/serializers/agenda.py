from rest_framework import serializers

from agenda.models import AgendaModel, Colors, Reminder


class ColorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Colors
        fields = ["user", "cor_de_destaque", "cor_do_dia"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        request = self.context["request"]
        config, _ = Colors.objects.update_or_create(
            user=request.user,
            defaults=validated_data,
        )
        return config


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ["descricao", "agenda"]

    def create(self, validated_data):
        request = self.context["request"]
        return super().create(validated_data)


class AgendaModelSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AgendaModel
        fields = [
            "id",
            "user",
            "titulo",
            "descricao",
            "tipo_de_evento",
            "importancia",
            "dia_do_evento",
            "email_notification_at",
            "email_notification_message",
            "email_notification_sent_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "email_notification_sent_at",
            "created_at",
            "updated_at",
            "is_active",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = request.user
        return super().create(validated_data)

    def validate(self, attrs):
        notification_at = attrs.get(
            "email_notification_at",
            getattr(self.instance, "email_notification_at", None),
        )
        if notification_at and not self.context["request"].user.email:
            raise serializers.ValidationError(
                {"email_notification_at": "Cadastre um e-mail para receber notificações."}
            )
        return attrs

    def update(self, instance, validated_data):
        notification_changed = any(
            field in validated_data and validated_data[field] != getattr(instance, field)
            for field in ("email_notification_at", "email_notification_message")
        )
        if notification_changed:
            validated_data["email_notification_sent_at"] = None
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Limpa eventuais tuplas salvas como string legacy no banco
        tipo = data.get("tipo_de_evento", "")
        if isinstance(tipo, str) and tipo.startswith("(") and "," in tipo:
            import ast

            try:
                parsed = ast.literal_eval(tipo)
                if isinstance(parsed, (tuple, list)) and parsed:
                    data["tipo_de_evento"] = str(parsed[0])
            except Exception:
                pass
        imp = data.get("importancia", "")
        if isinstance(imp, str) and imp.startswith("(") and "," in imp:
            import ast

            try:
                parsed = ast.literal_eval(imp)
                if isinstance(parsed, (tuple, list)) and parsed:
                    data["importancia"] = str(parsed[0])
            except Exception:
                pass
        return data
