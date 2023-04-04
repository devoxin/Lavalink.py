from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Union

from .server import AudioTrack

if TYPE_CHECKING:
    from .client import Client
    from .node import Node
    from .player import LoadResult


class BasePlayer(ABC):
    """
    Represents the BasePlayer all players must be inherited from.

    Attributes
    ----------
    guild_id: :class:`int`
        The guild id of the player.
    node: :class:`Node`
        The node that the player is connected to.
    channel_id: Optional[:class:`int`]
        The ID of the voice channel the player is connected to.
        This could be None if the player isn't connected.
    """
    def __init__(self, guild_id: int, node: 'Node'):
        self.client: 'Client' = node.manager.client
        self.guild_id: int = guild_id
        self.node: 'Node' = node
        self.channel_id: Optional[int] = None

        self._internal_id: str = str(guild_id)
        self._original_node: Optional['Node'] = None  # This is used internally for failover.
        self._voice_state = {}

    @abstractmethod
    async def _handle_event(self, event):
        raise NotImplementedError

    @abstractmethod
    async def _update_state(self, state: dict):
        raise NotImplementedError

    async def play_track(self, track: str, start_time: Optional[int] = None, end_time: Optional[int] = None,
                         no_replace: Optional[bool] = None, volume: Optional[int] = None, pause: Optional[bool] = None,
                         **kwargs):
        """|coro|

        Plays the given track.

        Parameters
        ----------
        track: :class:`str`
            The track to play. This must be the base64 string from a track.
        start_time: Optional[:class:`int`]
            The number of milliseconds to offset the track by.
            If left unspecified or ``None`` is provided, the track will start from the beginning.
        end_time: Optional[:class:`int`]
            The position at which the track should stop playing.
            This is an absolute position, so if you want the track to stop at 1 minute, you would pass 60000.
            The default behaviour is to play until no more data is received from the remote server.
            If left unspecified or ``None`` is provided, the default behaviour is exhibited.
        no_replace: Optional[:class:`bool`]
            If set to true, operation will be ignored if a track is already playing or paused.
            The default behaviour is to always replace.
            If left unspecified or None is provided, the default behaviour is exhibited.
        volume: Optional[:class:`int`]
            The initial volume to set. This is useful for changing the volume between tracks etc.
            If left unspecified or ``None`` is provided, the volume will remain at its current setting.
        pause: Optional[:class:`bool`]
            Whether to immediately pause the track after loading it.
            The default behaviour is to never pause.
            If left unspecified or ``None`` is provided, the default behaviour is exhibited.
        **kwargs: :class:`any`
            The kwargs to use when playing. You can specify any extra parameters that may be
            used by plugins, which offer extra features not supported out-of-the-box by Lavalink.py.
        """
        if track is None or not isinstance(track, str):
            raise ValueError('track must be a str')

        options = kwargs

        if start_time is not None:
            if not isinstance(start_time, int) or start_time < 0:
                raise ValueError('start_time must be an int with a value equal to, or greater than 0')

            options['position'] = start_time

        if end_time is not None:
            if not isinstance(end_time, int) or not end_time >= 1:
                raise ValueError('end_time must be an int with a value equal to, or greater than 1')

            options['end_time'] = end_time

        if no_replace is not None:
            if not isinstance(no_replace, bool):
                raise TypeError('no_replace must be a bool')

            options['no_replace'] = no_replace

        if volume is not None:
            if not isinstance(volume, int):
                raise TypeError('volume must be an int')

            self.volume = max(min(volume, 1000), 0)
            options['volume'] = self.volume

        if pause is not None:
            if not isinstance(pause, bool):
                raise TypeError('pause must be a bool')

            options['paused'] = pause

        await self.node.update_player(self._internal_id, encoded_track=track, **options)

    def cleanup(self):
        pass

    async def destroy(self):
        """|coro|

        Destroys the current player instance.

        Shortcut for :func:`PlayerManager.destroy`.
        """
        await self.client.player_manager.destroy(self.guild_id)

    async def _voice_server_update(self, data):
        self._voice_state.update(endpoint=data['endpoint'], token=data['token'])
        await self._dispatch_voice_update()

    async def _voice_state_update(self, data):
        raw_channel_id = data['channel_id']
        self.channel_id = int(raw_channel_id) if raw_channel_id else None

        if not self.channel_id:  # We're disconnecting
            self._voice_state.clear()
            return

        if data['session_id'] != self._voice_state.get('sessionId'):
            self._voice_state.update(sessionId=data['session_id'])

            await self._dispatch_voice_update()

    async def _dispatch_voice_update(self):
        if {'sessionId', 'endpoint', 'token'} == self._voice_state.keys():
            await self.node.update_player(self._internal_id, voice_state=self._voice_state)

    @abstractmethod
    async def node_unavailable(self):
        """|coro|

        Called when a player's node becomes unavailable.
        Useful for changing player state before it's moved to another node.
        """
        raise NotImplementedError

    @abstractmethod
    async def change_node(self, node: 'Node'):
        """|coro|

        Called when a node change is requested for the current player instance.

        Parameters
        ----------
        node: :class:`Node`
            The new node to switch to.
        """
        raise NotImplementedError


class DeferredAudioTrack(ABC, AudioTrack):
    """
    Similar to an :class:`AudioTrack`, however this track only stores metadata up until it's
    played, at which time :func:`load` is called to retrieve a base64 string which is then used for playing.

    Note
    ----
    For implementation: The ``track`` field need not be populated as this is done later via
    the :func:`load` method. You can optionally set ``self.track`` to the result of :func:`load`
    during implementation, as a means of caching the base64 string to avoid fetching it again later.
    This should serve the purpose of speeding up subsequent play calls in the event of repeat being enabled,
    for example.
    """
    @abstractmethod
    async def load(self, client: 'Client'):
        """|coro|

        Retrieves a base64 string that's playable by Lavalink.
        For example, you can use this method to search Lavalink for an identical track from other sources,
        which you can then use the base64 string of to play the track on Lavalink.

        Parameters
        ----------
        client: :class:`Client`
            This will be an instance of the Lavalink client 'linked' to this track.

        Returns
        -------
        :class:`str`
            A Lavalink-compatible base64-encoded string containing track metadata.
        """
        raise NotImplementedError


class Source(ABC):
    def __init__(self, name: str):
        self.name: str = name

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.name == other.name

        raise NotImplementedError

    def __hash__(self):
        return hash(self.name)

    @abstractmethod
    async def load_item(self, client: 'Client', query: str) -> Optional['LoadResult']:
        """|coro|

        Loads a track with the given query.

        Parameters
        ----------
        client: :class:`Client`
            The Lavalink client. This could be useful for performing a Lavalink search
            for an identical track from other sources, if needed.
        query: :class:`str`
            The search query that was provided.

        Returns
        -------
        Optional[:class:`LoadResult`]
            A LoadResult, or None if there were no matches for the provided query.
        """
        raise NotImplementedError

    def __repr__(self):
        return '<Source name={0.name}>'.format(self)


class Filter:
    def __init__(self, values: Union[dict, list, float]):
        self.values = values

    def update(self, **kwargs):
        """ Updates the internal values to match those provided. """
        raise NotImplementedError

    def serialize(self) -> dict:
        """ Transforms the internal values into a dict matching the structure Lavalink expects. """
        raise NotImplementedError
