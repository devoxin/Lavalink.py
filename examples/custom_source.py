from lavalink.models import (DeferredAudioTrack, LoadResult, LoadType,
                             PlaylistInfo, Source)


class LoadError(Exception):  # We'll raise this if we have trouble loading our track.
    pass


class CustomAudioTrack(DeferredAudioTrack):
    # A DeferredAudioTrack allows us to load metadata now, and a playback URL later.
    # This makes the DeferredAudioTrack highly efficient, particularly in cases
    # where large playlists are loaded.

    async def load(self, client):  # Load our 'actual' playback track using the metadata from this one.
        result: LoadResult = await client.get_tracks('ytsearch:{0.title} {0.author}'.format(self))  # Search for our track on YouTube.

        if result.load_type != LoadType.SEARCH or not result.tracks:  # We're expecting a 'SEARCH' due to our 'ytsearch' prefix above.
            raise LoadError

        first_track = result.tracks[0]  # Grab the first track from the results.
        base64 = first_track.track  # Extract the base64 string from the track.
        self.track = base64  # We'll store this for later, as it allows us to save making network requests
        # if this track is re-used (e.g. repeat).

        return base64


class CustomSource(Source):
    def __init__(self):
        super().__init__(name='custom')  # Initialising our custom source with the name 'source'.

    async def load_item(self, client, query: str):
        track = CustomAudioTrack({  # Create an instance of our CustomAudioTrack.
            'identifier': '27cgqh0VRhVeM61ugTnorD',  # Fill it with metadata that we've obtained from our source's provider.
            'isSeekable': True,
            'author': 'DJ Seinfeld',
            'length': 296000,
            'isStream': False,
            'title': 'These Things Will Come To Be',
            'uri': 'https://open.spotify.com/track/27cgqh0VRhVeM61ugTnorD'
            }, requester=0)  # Init requester with a default value.
        return LoadResult(LoadType.TRACK, [track], playlist_info=PlaylistInfo.none())
