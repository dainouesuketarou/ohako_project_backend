from django.urls import path
from .views import (
    UserLoginView, UserPlaylistsView, TrackRecommendationView,
    AddTrackToPlaylistView, UserRegistrationView, RemoveTrackFromPlaylistView, TrackRecommendationByTempoView,
    TrackSearchView
)
from api.views import spotify_callback

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    # path('logout/', LogoutView.as_view(), name='logout'),
    path('playlists/', UserPlaylistsView.as_view(), name='user-playlists'),
    path('search/', TrackSearchView.as_view(), name='track-search'),
    path('recommendations/', TrackRecommendationView.as_view(), name='track-recommendations'),
    path('recommendations_by_tempo/', TrackRecommendationByTempoView.as_view(), name='track_recommendations_by_tempo'),
    path('add_track/', AddTrackToPlaylistView.as_view(), name='add-track-to-playlist'),
    path('remove_track/', RemoveTrackFromPlaylistView.as_view(), name='remove_track_from_playlist'),
    path('callback/', spotify_callback, name='spotify-callback'),
]
