from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Track, Playlist

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')

class TrackModelTest(TestCase):
    def setUp(self):
        self.track = Track.objects.create(spotify_id='testid', name='testtrack', artists='testartist', album_name='testalbum')

    def test_track_creation(self):
        self.assertEqual(self.track.spotify_id, 'testid')
        self.assertEqual(self.track.name, 'testtrack')

class PlaylistModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.playlist = Playlist.objects.create(user=self.user, name='testplaylist')
        self.track = Track.objects.create(spotify_id='testid', name='testtrack', artists='testartist', album_name='testalbum')

    def test_playlist_creation(self):
        self.assertEqual(self.playlist.name, 'testplaylist')

    def test_add_track_to_playlist(self):
        self.playlist.tracks.add(self.track)
        self.assertIn(self.track, self.playlist.tracks.all())