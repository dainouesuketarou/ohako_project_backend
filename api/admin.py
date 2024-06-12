from django.contrib import admin
from .models import User, Playlist, Track

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'date_joined', 'is_active', 'is_staff')
    readonly_fields = ('date_joined',)

admin.site.register(User, UserAdmin)
admin.site.register(Track)
admin.site.register(Playlist)
