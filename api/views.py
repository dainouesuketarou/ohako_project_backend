import spotipy
from rest_framework_simplejwt.exceptions import TokenError
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import User, Playlist, Track
from .serializers import UserSerializer
from django.contrib.auth import authenticate, logout
import logging
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import time

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

class UserRegistrationView(generics.CreateAPIView):
    # queryset属性はこのビューで操作するデータ群を定義するための属性で、ここではUserオブジェクト全体を指定している
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        print("perform_createメソッド実行開始")
        user = serializer.save()
        Playlist.objects.create(user=user)

    # こちらのcreateメソッドはこのビューにPOSTリクエストが投げられた時に機能する
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        user = serializer.instance
        refresh = RefreshToken.for_user(user)
        response_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data  # シリアライズされたユーザーデータを含める
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        return Response({"error": "Username or password is incorrect"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            # リクエストからリフレッシュトークンを取得
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()

            # Djangoのセッションログアウト
            logout(request)

            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserPlaylistsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            playlist = request.user.playlist
            track_ids = playlist.tracks.values_list('spotify_id', flat=True)

            sp = get_spotify_client()

            # Filter out empty or None values
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
                for track in tracks_info if track['id']  # Ensure track id is valid
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
        retries = 5

        for attempt in range(retries):
            try:
                results = sp.search(q=track_name, limit=1, type='track', market='JP')
                if not results['tracks']['items']:
                    logger.error("Track not found")
                    return Response({"error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

                track = results['tracks']['items'][0]
                track_id = track['id']
                audio_features = sp.audio_features([track_id])
                if not audio_features or not audio_features[0]:
                    logger.error("Audio features not found")
                    return Response({"error": "Audio features not found"}, status=status.HTTP_404_NOT_FOUND)

                track_key = audio_features[0]['key']

                recommendations = sp.recommendations(seed_tracks=[track_id], limit=50, market='JP')
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
                logger.info(f"Recommendations for {track_name} with key {track_key} or {track_key - 1}: {sorted_tracks}")

                return Response(sorted_tracks, status=status.HTTP_200_OK)

            except spotipy.SpotifyException as e:
                if e.http_status == 429:
                    retry_after = int(e.headers.get("Retry-After", 1))
                    logger.warning(f"Rate limited by Spotify API. Retrying in {retry_after} seconds.")
                    time.sleep(retry_after)
                else:
                    logger.error(f"Error fetching recommendations (attempt {attempt+1}/{retries}): {e}")
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error fetching recommendations (attempt {attempt+1}/{retries}): {e}")
                time.sleep(1)

        return Response({"error": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrackRecommendationByTempoView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        track_name = request.query_params.get('track_name')
        if not track_name:
            return Response({"error": "Track name is required"}, status=status.HTTP_400_BAD_REQUEST)

        sp = get_spotify_client()
        retries = 5
        delay = 1  # 初期遅延時間（秒）

        for attempt in range(retries):
            try:
                # 日本市場を指定してトラックを検索
                results = sp.search(q=track_name, limit=1, type='track', market='JP')
                if not results['tracks']['items']:
                    logger.error("Track not found")
                    return Response({"error": "Track not found"}, status=status.HTTP_404_NOT_FOUND)

                track = results['tracks']['items'][0]
                track_id = track['id']
                audio_features = sp.audio_features([track_id])
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
                logger.error(f"Error fetching recommendations (attempt {attempt+1}/{retries}): {e}")
                time.sleep(delay)
                delay *= 2  # エクスポネンシャルバックオフ

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
