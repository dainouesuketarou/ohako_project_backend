from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from .models import User, Playlist, Track

class UserRegistrationViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.valid_payload = {
            'username': 'testuser',
            'password': 'testpassword'
        }

    def test_register_user(self):
        response = self.client.post(reverse('user-register'), data=self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')

class UserLoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.valid_payload = {
            'username': 'testuser',
            'password': 'testpassword'
        }

    def test_login_user(self):
        response = self.client.post(reverse('user-login'), data=self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

class PlaylistViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.playlist = Playlist.objects.create(user=self.user, name='testplaylist')

    def test_get_user_playlists(self):
        response = self.client.get(reverse('user-playlists'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['playlist_name'], 'testplaylist')