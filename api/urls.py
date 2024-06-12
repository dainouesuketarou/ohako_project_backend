from django.urls import path
from .views import (
    LogoutView,
    UserPlaylistsView,
    TrackSearchView,
    TrackRecommendationView,
    TrackRecommendationByTempoView,
    AddTrackToPlaylistView,  # ここを確認
    RemoveTrackFromPlaylistView,
    update_user,
    get_follow_data,
    spotify_callback, UpdateProfileImageView, track_users, follow_user, unfollow_user, get_user_playlist, login,
    register,
)

urlpatterns = [
    path('login/', login, name='login'),
    path('register/', register, name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('playlists/', UserPlaylistsView.as_view(), name='user-playlists'),
    path('search/', TrackSearchView.as_view(), name='track-search'),
    path('recommendations/', TrackRecommendationView.as_view(), name='track-recommendations'),
    path('recommendations_by_tempo/', TrackRecommendationByTempoView.as_view(), name='track_recommendations_by_tempo'),
    path('add_track/', AddTrackToPlaylistView.as_view(), name='add-track-to-playlist'),  # ここを確認
    path('remove_track/', RemoveTrackFromPlaylistView.as_view(), name='remove_track_from_playlist'),
    path('callback/', spotify_callback, name='spotify-callback'),
    path('update_user/', update_user, name='update-user'),
    path('follow_data/', get_follow_data, name='follow-data'),
    path('update_profile_image/', UpdateProfileImageView.as_view(), name='update-profile-image'),
    path('track_users/<str:track_id>/', track_users, name='track-users'),
    path('follow_user/', follow_user, name='follow-user'),
    path('unfollow_user/', unfollow_user, name='unfollow-user'),
    path('user_playlist/<int:user_id>/', get_user_playlist, name='user-playlist'),
]