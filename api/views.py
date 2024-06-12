import spotipy
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import User, Playlist, Track
from .serializers import UserSerializer, TrackSerializer, PlaylistSerializer
from django.contrib.auth import authenticate, logout
from django.shortcuts import get_object_or_404, redirect
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import logging
import time
from rest_framework.parsers import MultiPartParser, FormParser

logger = logging.getLogger(__name__)

def get_spotify_client():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI,
    ))
    return sp

@csrf_exempt
def spotify_callback(request):
    sp_oauth = SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI
    )
    code = request.GET.get('code')
    if code:
        try:
            token_info = sp_oauth.get_access_token(code)
            if token_info:
                return redirect('http://localhost:3000/playlists')  # フロントエンドのプレイリストページにリダイレクト
        except Exception as e:
            logger.error(f"Spotify authentication error: {e}")
            return HttpResponse(f'Authentication failed: {e}', status=400)
    return HttpResponse('Authentication failed', status=400)

@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)

    if user is not None:
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': user_data
        })
    else:
        return Response({'error': 'Invalid credentials'}, status=400)


@api_view(['POST'])
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=400)

    user = User.objects.create_user(username=username, password=password)
    user.save()

    # ユーザー登録時にプレイリストを作成
    playlist = Playlist.objects.create(user=user, name=f"{username}'s Playlist")
    playlist.save()

    refresh = RefreshToken.for_user(user)
    user_data = UserSerializer(user).data
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': user_data
    }, status=status.HTTP_201_CREATED)

# class UserRegistrationView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#     permission_classes = [AllowAny]
#
#     def perform_create(self, serializer):
#         user = serializer.save()
#         Playlist.objects.create(user=user)
#
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         user = serializer.instance
#         print(f"User password (hashed): {user.password}")  # パスワードのハッシュを確認
#         refresh = RefreshToken.for_user(user)
#         response_data = {
#             'refresh': str(refresh),
#             'access': str(refresh.access_token),
#             'user': UserSerializer(user).data
#         }
#         return Response(response_data, status=status.HTTP_201_CREATED)
#
# class UserLoginView(APIView):
#     def post(self, request, *args, **kwargs):
#         username = request.data.get('username')
#         password = request.data.get('password')
#         user = authenticate(username=username, password=password)
#         if user and user.is_active:
#             refresh = RefreshToken.for_user(user)
#             return Response({
#                 'refresh': str(refresh),
#                 'access': str(refresh.access_token),
#                 'user': UserSerializer(user).data,
#                 'message': 'Login successful'
#             }, status=status.HTTP_200_OK)
#         return Response({"error": "Username or password is incorrect"}, status=status.HTTP_401_UNAUTHORIZED)

class UserPlaylistsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            playlist = request.user.playlist
            track_ids = playlist.tracks.values_list('spotify_id', flat=True)

            sp = get_spotify_client()

            valid_track_ids = [track_id for track_id in track_ids if track_id]

            if not valid_track_ids:
                return Response({"playlist_name": playlist.name, "tracks": []}, status=status.HTTP_200_OK)

            tracks_info = sp.tracks(valid_track_ids)['tracks']

            tracks_data = [
                {
                    'spotify_id': track['id'],
                    'name': track['name'],
                    'artists': ', '.join(artist['name'] for artist in track['artists']),
                    'album_name': track['album']['name'],
                    'album_image': track['album']['images'][0]['url'] if track['album']['images'] else None
                }
                for track in tracks_info if track['id']
            ]

            return Response({"playlist_name": playlist.name, "tracks": tracks_data}, status=status.HTTP_200_OK)
        except Playlist.DoesNotExist:
            return Response({"error": "User does not have a playlist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrackSearchView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        query = request.query_params.get('query')
        if not query:
            return Response({"error": "Query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        sp = get_spotify_client()
        try:
            results = sp.search(q=query, limit=10, type='track', market='JP')
            tracks = [
                {
                    "spotify_id": track['id'],
                    "name": track['name'],
                    "artists": ', '.join(artist['name'] for artist in track['artists']),
                    "album_name": track['album']['name'],
                    "album_image": track['album']['images'][0]['url'] if track['album']['images'] else None
                }
                for track in results['tracks']['items']
            ]
            return Response(tracks, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error searching tracks: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrackRecommendationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        track_name = request.query_params.get('track_name')
        if not track_name:
            return Response({"error": "Track name is required"}, status=status.HTTP_400_BAD_REQUEST)

        sp = get_spotify_client()

        try:
            results = sp.search(q=track_name, limit=1, type='track', market='JP')
            logger.debug(f"Spotify search results: {results}")

            if not results['tracks']['items']:
                return Response({"error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

            track = results['tracks']['items'][0]
            track_data = {
                "id": track['id'],
                "name": track['name'],
                "artists": [artist['name'] for artist in track['artists']],
                "album_name": track['album']['name'],
                "album_image": track['album']['images'][0]['url'] if track['album']['images'] else None
            }

            audio_features = sp.audio_features([track['id']])
            logger.debug(f"Spotify audio features: {audio_features}")

            if not audio_features or not audio_features[0]:
                return Response({"error": "Audio features not found"}, status=status.HTTP_404_NOT_FOUND)

            track_key = audio_features[0]['key']

            recommendations = sp.recommendations(seed_tracks=[track['id']], limit=50, market='JP')
            recommendation_ids = [rec['id'] for rec in recommendations['tracks']]
            recommendation_features = sp.audio_features(recommendation_ids)

            tracks = [
                {
                    "name": rec['name'],
                    "artists": [artist['name'] for artist in rec['artists']],
                    "id": rec['id'],
                    "popularity": rec['popularity'],
                    "album_name": rec['album']['name'],
                    "album_image": rec['album']['images'][0]['url'],
                    "key": feature['key']
                }
                for rec, feature in zip(recommendations['tracks'], recommendation_features)
                if feature and (feature['key'] == track_key or feature['key'] == (track_key - 1) % 12)
            ]

            sorted_tracks = sorted(tracks, key=lambda x: x['popularity'], reverse=True)[:10]

            return Response({
                "track_info": track_data,
                "recommendations": sorted_tracks
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching track recommendations: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrackRecommendationByTempoView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        track_name = request.query_params.get('track_name')
        if not track_name:
            return Response({"error": "Track name is required"}, status=status.HTTP_400_BAD_REQUEST)

        sp = get_spotify_client()
        retries = 5
        delay = 1

        for attempt in range(retries):
            try:
                results = sp.search(q=track_name, limit=1, type='track', market='JP')
                logger.debug(f"Spotify search results: {results}")

                if not results['tracks']['items']:
                    logger.error("Track not found")
                    return Response({"error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

                track = results['tracks']['items'][0]
                track_id = track['id']
                audio_features = sp.audio_features([track_id])
                logger.debug(f"Spotify audio features: {audio_features}")

                if not audio_features or not audio_features[0]:
                    logger.error("Audio features not found")
                    return Response({"error": "Audio features not found"}, status=status.HTTP_404_NOT_FOUND)

                track_tempo = audio_features[0]['tempo']

                recommendations = sp.recommendations(seed_tracks=[track_id], limit=50, market='JP')
                tracks = []
                for rec in recommendations['tracks']:
                    rec_audio_features = sp.audio_features([rec['id']])
                    if rec_audio_features and abs(rec_audio_features[0]['tempo'] - track_tempo) <= 10:
                        tracks.append({
                            "name": rec['name'],
                            "artists": [artist['name'] for artist in rec['artists']],
                            "id": rec['id'],
                            "popularity": rec['popularity'],
                            "album_name": rec['album']['name'],
                            "album_image": rec['album']['images'][0]['url'],
                            "tempo": rec_audio_features[0]['tempo']
                        })

                sorted_tracks = sorted(tracks, key=lambda x: x['popularity'], reverse=True)
                logger.info(f"Recommendations for {track_name} with tempo {track_tempo}: {sorted_tracks}")

                return Response(sorted_tracks, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Error fetching recommendations (attempt {attempt + 1}/{retries}): {e}")
                time.sleep(delay)
                delay *= 2

        return Response({"error": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AddTrackToPlaylistView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        track_id = request.data.get('track_id')

        if not track_id:
            return Response({"error": "Track ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            playlist = request.user.playlist
            track, created = Track.objects.get_or_create(spotify_id=track_id)
            playlist.tracks.add(track)
            playlist.save()

            return Response({"message": "Track added to playlist"}, status=status.HTTP_200_OK)
        except Playlist.DoesNotExist:
            return Response({"error": "User does not have a playlist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RemoveTrackFromPlaylistView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        track_id = request.data.get('track_id')

        if not track_id:
            return Response({"error": "Track ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            playlist = request.user.playlist
            track = Track.objects.get(spotify_id=track_id)

            if track in playlist.tracks.all():
                playlist.tracks.remove(track)
                return Response({"message": "Track removed from playlist"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Track not found in playlist"}, status=status.HTTP_404_NOT_FOUND)

        except Track.DoesNotExist:
            return Response({"error": "Track does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Playlist.DoesNotExist:
            return Response({"error": "User does not have a playlist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_follow_data(request):
    try:
        user = request.user
        following = user.following.all()
        followers_count = user.followers.count()
        following_count = user.following.count()
        data = {
            'following': UserSerializer(following, many=True).data,
            'followers_count': followers_count,
            'following_count': following_count,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching follow data: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user(request):
    user = request.user
    data = request.data

    if 'username' in data:
        user.username = data['username']

    if 'profile_image' in data and isinstance(data['profile_image'], str):
        from django.core.files.base import ContentFile
        import base64
        format, imgstr = data['profile_image'].split(';base64,')
        ext = format.split('/')[-1]
        user.profile_image = ContentFile(base64.b64decode(imgstr), name=f"{user.username}.{ext}")

    user.save()

    # 画像が存在する場合のみURLを出力
    if user.profile_image:
        print(user.profile_image.url)

    return Response(UserSerializer(user).data)



class UpdateProfileImageView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, format=None):
        user = request.user
        if 'profile_image' in request.data:
            user.profile_image = request.data['profile_image']
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            logout(request)
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrackDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, track_id, format=None):
        sp = get_spotify_client()
        try:
            track = sp.track(track_id)
            track_data = {
                "spotify_id": track['id'],
                "name": track['name'],
                "artists": ', '.join(artist['name'] for artist in track['artists']),
                "album_name": track['album']['name'],
                "album_image": track['album']['images'][0]['url'] if track['album']['images'] else None
            }
            return Response(track_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching track details: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def track_users(request, track_id):
    current_user = request.user
    users = User.objects.filter(playlist__tracks__spotify_id=track_id).exclude(id=current_user.id).distinct()
    data = [{'id': user.id, 'username': user.username, 'profile_image': user.profile_image.url if user.profile_image else None} for user in users]
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_user(request):
    try:
        user_id = request.data.get('user_id')
        target_user = User.objects.get(id=user_id)
        request.user.following.add(target_user)
        return Response({'message': 'フォローしました'}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': '対象ユーザーが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unfollow_user(request):
    try:
        user_id = request.data.get('user_id')
        target_user = User.objects.get(id=user_id)
        request.user.following.remove(target_user)
        return Response({'message': 'フォローを外しました'}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': '対象ユーザーが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

def get_spotify_track_info(spotify_id):
    sp = get_spotify_client()
    track = sp.track(spotify_id)
    if track:
        return {
            "spotify_id": track["id"],
            "name": track["name"],
            "artists": ", ".join(artist["name"] for artist in track["artists"]),
            "album_name": track["album"]["name"],
            "album_image": track["album"]["images"][0]["url"] if track["album"]["images"] else None
        }
    return None

@api_view(['GET'])
def get_user_playlist(request, user_id):
    try:
        user = User.objects.get(pk=user_id)
        playlist = Playlist.objects.get(user=user)
        track_data = []
        for track in playlist.tracks.all():
            track_info = get_spotify_track_info(track.spotify_id)
            if track_info:
                track_data.append(track_info)
        return Response({"id": playlist.id, "name": playlist.name, "tracks": track_data}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Playlist.DoesNotExist:
        return Response({'error': 'Playlist not found'}, status=status.HTTP_404_NOT_FOUND)