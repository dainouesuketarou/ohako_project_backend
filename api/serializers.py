from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Track

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = ['spotify_id', 'name', 'artists', 'album_name']
