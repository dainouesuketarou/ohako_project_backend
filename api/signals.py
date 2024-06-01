from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Playlist

@receiver(post_save, sender=User)
def create_user_playlist(sender, instance, created, **kwargs):
    if created:
        Playlist.objects.create(user=instance)