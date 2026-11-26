from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from rest_framework import serializers

from .models import Link
from .utils import RESERVED_CODES, generate_code


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LinkSerializer(serializers.ModelSerializer):
    short_url = serializers.SerializerMethodField()
    short_code = serializers.CharField(
        required=False,
        min_length=3,
        max_length=20,
        validators=[RegexValidator(r"^[0-9A-Za-z_-]+$", "Use letters, digits, - or _ only.")],
    )

    class Meta:
        model = Link
        fields = [
            "id", "original_url", "short_code", "short_url",
            "click_count", "created_at", "expires_at", "is_active",
        ]
        read_only_fields = ["click_count", "created_at", "is_active"]

    def get_short_url(self, obj):
        request = self.context.get("request")
        path = f"/{obj.short_code}/"
        return request.build_absolute_uri(path) if request else path

    def validate_short_code(self, value):
        if value.lower() in RESERVED_CODES:
            raise serializers.ValidationError("This alias is reserved.")
        if Link.objects.filter(short_code=value).exists():
            raise serializers.ValidationError("This alias is already taken.")
        return value

    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiry must be in the future.")
        return value

    def create(self, validated_data):
        if not validated_data.get("short_code"):
            code = generate_code()
            while Link.objects.filter(short_code=code).exists() or code.lower() in RESERVED_CODES:
                code = generate_code()
            validated_data["short_code"] = code
        return super().create(validated_data)


class LinkUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = ["is_active", "expires_at"]
