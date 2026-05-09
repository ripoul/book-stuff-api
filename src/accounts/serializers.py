from django.contrib.auth.models import User
from rest_framework import serializers


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ("id", "email", "password")
        read_only_fields = ("id",)

    def validate_email(self, value):
        v = value.strip().lower()
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError()
        return v

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        return User.objects.create_user(
            username=email,
            email=email,
            password=password,
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")
        read_only_fields = ("id", "username")

    def validate_email(self, value):
        v = value.strip().lower()
        qs = User.objects.filter(username=v)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError()
        return v

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        email_present = "email" in validated_data
        user = super().update(instance, validated_data)
        update_fields = []
        if email_present:
            user.username = user.email
            update_fields.append("username")
        if password is not None:
            user.set_password(password)
            update_fields.append("password")
        if update_fields:
            user.save(update_fields=update_fields)
        return user
