from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Track, Playlist

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'profile_image', 'is_staff', 'is_superuser']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            is_staff=validated_data.get('is_staff', False),
            is_superuser=validated_data.get('is_superuser', False)
        )
        user.set_password(validated_data['password'])  # パスワードをハッシュ化
        user.save()
        return user

class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = ['spotify_id', 'name', 'artists', 'album_name']

class PlaylistSerializer(serializers.ModelSerializer):
    tracks = TrackSerializer(many=True)

    class Meta:
        model = Playlist
        fields = ['id', 'name', 'tracks']
