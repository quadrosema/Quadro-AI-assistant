import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from colorama import Fore

load_dotenv()

SCOPE = "user-read-playback-state,user-modify-playback-state,user-read-currently-playing,user-library-read"

class SpotifySkills:
    def __init__(self):
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
                scope=SCOPE,
                cache_path="data/.spotify_cache"
            ))
            # Test connection
            try:
                self.sp.current_user()
                print("   ✅ Spotify Skills Online")
            except Exception:
                print("   ⚠️ Spotify Offline (will retry later)")
        except Exception as e:
            print(Fore.RED + f"   ❌ Spotify init error: {e}")
            self.sp = None

    def _get_device(self):
        """Get the active Spotify device, or return error message."""
        if not self.sp:
            return None, "Spotify not authenticated."
        
        devices = self.sp.devices()
        if not devices['devices']:
            return None, "No active Spotify devices found. Open Spotify somewhere first."
        
        # Prefer the currently active device, otherwise use the first one
        active = next((d for d in devices['devices'] if d['is_active']), None)
        device = active or devices['devices'][0]
        return device['id'], None

    def play_pause(self):
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            playback = self.sp.current_playback()
            if playback and playback['is_playing']:
                self.sp.pause_playback(device_id=device_id)
                return "Paused Spotify."
            else:
                self.sp.start_playback(device_id=device_id)
                return "Resuming Spotify."
        except Exception as e:
            return f"Spotify error: {e}"

    def next_track(self):
        device_id, error = self._get_device()
        if error:
            return error
        try:
            self.sp.next_track(device_id=device_id)
            return "Skipped to next track."
        except Exception as e:
            return f"Spotify error: {e}"

    def previous_track(self):
        device_id, error = self._get_device()
        if error:
            return error
        try:
            self.sp.previous_track(device_id=device_id)
            return "Going back a track."
        except Exception as e:
            return f"Spotify error: {e}"

    def play_song(self, query):
        """Search for a song and play it."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            if not results['tracks']['items']:
                return f"Couldn't find '{query}' on Spotify."
            
            track_uri = results['tracks']['items'][0]['uri']
            track_name = results['tracks']['items'][0]['name']
            artist = results['tracks']['items'][0]['artists'][0]['name']
            
            self.sp.start_playback(device_id=device_id, uris=[track_uri])
            return f"Playing '{track_name}' by {artist}."
        except Exception as e:
            return f"Spotify error: {e}"

    def play_artist(self, query):
        """Play an artist's top tracks."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            results = self.sp.search(q=query, type='artist', limit=1)
            if not results['artists']['items']:
                return f"Couldn't find artist '{query}'."
            
            artist_uri = results['artists']['items'][0]['uri']
            artist_name = results['artists']['items'][0]['name']
            
            self.sp.start_playback(device_id=device_id, context_uri=artist_uri)
            return f"Playing {artist_name}."
        except Exception as e:
            return f"Spotify error: {e}"

    def play_album(self, query):
        """Play an album."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            results = self.sp.search(q=query, type='album', limit=1)
            if not results['albums']['items']:
                return f"Couldn't find album '{query}'."
            
            album_uri = results['albums']['items'][0]['uri']
            album_name = results['albums']['items'][0]['name']
            artist = results['albums']['items'][0]['artists'][0]['name']
            
            self.sp.start_playback(device_id=device_id, context_uri=album_uri)
            return f"Playing '{album_name}' by {artist}."
        except Exception as e:
            return f"Spotify error: {e}"

    def play_liked_songs(self):
        """Shuffle user's liked songs."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            # Get saved tracks
            results = self.sp.current_user_saved_tracks(limit=50)
            if not results['items']:
                return "You don't have any liked songs."
            
            track_uris = [item['track']['uri'] for item in results['items']]
            self.sp.start_playback(device_id=device_id, uris=track_uris)
            self.sp.shuffle(True, device_id=device_id)
            return "Playing your liked songs on shuffle."
        except Exception as e:
            return f"Spotify error: {e}"

    def set_volume(self, level):
        """Set Spotify volume (0-100)."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            self.sp.volume(level, device_id=device_id)
            return f"Spotify volume set to {level}%."
        except Exception as e:
            return f"Spotify error: {e}"

    def current_track(self):
        """Get info about what's currently playing."""
        try:
            playback = self.sp.current_playback()
            if not playback or not playback['item']:
                return "Nothing is playing right now."
            
            track = playback['item']['name']
            artist = playback['item']['artists'][0]['name']
            return f"Currently playing: '{track}' by {artist}."
        except Exception as e:
            return f"Spotify error: {e}"

    def shuffle(self, state):
        """Toggle shuffle on or off."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            self.sp.shuffle(state, device_id=device_id)
            return f"Shuffle {'on' if state else 'off'}."
        except Exception as e:
            return f"Spotify error: {e}"

    def repeat(self, state):
        """Set repeat mode: 'track', 'context', or 'off'."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            self.sp.repeat(state, device_id=device_id)
            return f"Repeat set to {state}."
        except Exception as e:
            return f"Spotify error: {e}"

    def add_to_queue(self, query):
        """Add a song to the queue."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            if not results['tracks']['items']:
                return f"Couldn't find '{query}'."
            
            track_uri = results['tracks']['items'][0]['uri']
            track_name = results['tracks']['items'][0]['name']
            
            self.sp.add_to_queue(track_uri, device_id=device_id)
            return f"Added '{track_name}' to queue."
        except Exception as e:
            return f"Spotify error: {e}"

    def play_playlist(self, query):
        """Search for a playlist and play it."""
        device_id, error = self._get_device()
        if error:
            return error
        
        try:
            results = self.sp.search(q=query, type='playlist', limit=1)
            if not results['playlists']['items']:
                return f"Couldn't find playlist '{query}'."
            
            playlist_uri = results['playlists']['items'][0]['uri']
            playlist_name = results['playlists']['items'][0]['name']
            
            self.sp.start_playback(device_id=device_id, context_uri=playlist_uri)
            return f"Playing playlist '{playlist_name}'."
        except Exception as e:
            return f"Spotify error: {e}"