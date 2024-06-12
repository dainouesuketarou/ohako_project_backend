from django.test import TestCase
from .models import Track, Playlist, User
from .serializers import UserSerializer, TrackSerializer, PlaylistSerializer

class UserSerializerTest(TestCase):
    def setUp(self):
        self.user_attributes = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        self.serializer_data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        self.user = User.objects.create(**self.user_attributes)
        self.serializer = UserSerializer(instance=self.user)

    def test_contains_expected_fields(self):
        data = self.serializer.data
        self.assertCountEqual(data.keys(), ['id', 'username', 'profile_image', 'following', 'followers'])

    def test_username_field_content(self):
        data = self.serializer.data
        self.assertEqual(data['username'], self.user_attributes['username'])

class TrackSerializerTest(TestCase):
    def setUp(self):
        self.track_attributes = {
            'spotify_id': 'testid',
            'name': 'testtrack',
            'artists': 'testartist',
            'album_name': 'testalbum'
        }
        self.track = Track.objects.create(**self.track_attributes)
        self.serializer = TrackSerializer(instance=self.track)

    def test_contains_expected_fields(self):
        data = self.serializer.data
        self.assertCountEqual(data.keys(), ['spotify_id', 'name', 'artists', 'album_name'])

    def test_track_field_content(self):
        data = self.serializer.data
        self.assertEqual(data['name'], self.track_attributes['name'])

class PlaylistSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='testuser', password='testpassword')
        self.playlist_attributes = {
            'user': self.user,
            'name': 'testplaylist'
        }
        self.playlist = Playlist.objects.create(**self.playlist_attributes)
        self.serializer = PlaylistSerializer(instance=self.playlist)

    def test_contains_expected_fields(self):
        data = self.serializer.data
        self.assertCountEqual(data.keys(), ['id', 'name', 'user', 'tracks'])

    def test_playlist_field_content(self):
        data = self.serializer.data
        self.assertEqual(data['name'], self.playlist_attributes['name'])