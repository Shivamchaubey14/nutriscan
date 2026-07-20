from typing import Any

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User


class RegisterSerializer(serializers.ModelSerializer[User]):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "password")

    def create(self, validated_data: dict[str, Any]) -> User:
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("id", "email", "date_joined")
