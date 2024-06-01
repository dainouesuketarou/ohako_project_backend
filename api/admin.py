from django.contrib import admin
from .models import User, Playlist, Track

admin.site.register(User)
admin.site.register(Track)
admin.site.register(Playlist)
