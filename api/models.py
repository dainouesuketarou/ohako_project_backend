from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)  # パスワードのハッシュ化
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    followers = models.ManyToManyField('self', symmetrical=False, related_name='following')

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username


class Track(models.Model):
    spotify_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    artists = models.CharField(max_length=255)
    album_name = models.CharField(max_length=255)

class Playlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='playlist')
    name = models.CharField(max_length=255, default='My Playlist')
    tracks = models.ManyToManyField(Track, related_name='playlists', blank=True)

    def __str__(self):
        return self.name