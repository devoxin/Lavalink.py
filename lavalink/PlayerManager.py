import asyncio
from abc import ABC, abstractmethod
from random import randrange

from .AudioTrack import AudioTrack
from .Events import QueueEndEvent, TrackExceptionEvent, TrackEndEvent, TrackStartEvent, TrackStuckEvent


class NoPreviousTrack(Exception):
    pass


class UnsupportedLavalinkVersion(Exception):
    pass


class Band:
    def __init__(self, band: int = 0, gain: float = 0.0):
        self.band = band
        self.gain = gain


class BasePlayer(ABC):
    def __init__(self, node, lavalink, guild_id: int):
        self.node = node
        self._lavalink = lavalink
        self.guild_id = str(guild_id)

        self._voice_state = {}
        self._voice_lock = asyncio.Event(loop=self._lavalink.loop)

    @abstractmethod
    async def handle_event(self, event):
        raise NotImplementedError

    def cleanup(self):
        pass

    async def ws_reset_handler(self):
        """ This method is called when WS receives a WebSocketClosedEvent with status code 4006 """
        pass


class DefaultPlayer(BasePlayer):
    def __init__(self, node, lavalink, guild_id: int):
        super().__init__(node, lavalink, guild_id)

        self._user_data = {}
        self.channel_id = None

        self.paused = False
        self.position = 0
        self._prev_position = 0
        self.position_timestamp = 0
        self.volume = 100
        self.shuffle = False
        self.repeat = False
        self.equalizer = [0.0 for x in range(15)]

        self.queue = []
        self.current = None
        self.previous = None

    @property
    def is_playing(self):
        """ Returns the player's track state. """
        return self.connected_channel is not None and self.current is not None

    @property
    def is_connected(self):
        """ Returns the player's connection state. """
        return self.connected_channel is not None

    @property
    def connected_channel(self):
        """ Returns the voice channel the player is connected to. """
        if not self.channel_id:
            return None

        return self._lavalink.bot.get_channel(int(self.channel_id))

    async def connect(self, channel_id: int):
        """ Connects to a voice channel. """
        ws = self._lavalink.bot._connection._get_websocket(int(self.guild_id))
        await ws.voice_state(self.guild_id, str(channel_id))
        await self.reset_equalizer()

    async def disconnect(self):
        """ Disconnects from the voice channel, if any. """
        if not self.is_connected:
            return
        self.channel_id = None

        await self.stop()

        ws = self._lavalink.bot._connection._get_websocket(int(self.guild_id))
        await ws.voice_state(self.guild_id, None)
        self._voice_state = {}
        self._voice_lock.clear()

    async def ws_reset_handler(self):
        """ This method is called when WS receives a WebSocketClosedEvent with status code 4006 """
        current_channel = int(self.channel_id)
        current_position = int(self.position)
        ws = self._lavalink.bot._connection._get_websocket(int(self.guild_id))
        self._voice_lock.clear()
        await ws.voice_state(int(self.guild_id), None)
        try:
            await asyncio.wait_for(self._voice_lock.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            pass
        finally:
            self._voice_state = {}
            self._voice_lock.clear()
        if current_channel:
            self._voice_lock.clear()
            await ws.voice_state(int(self.guild_id), str(current_channel))
            try:
                await asyncio.wait_for(self._voice_lock.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                self.channel_id = None
            else:
                self.queue.insert(0, self.current)
                await self.play()
                await self.seek(current_position)
            finally:
                self._voice_lock.clear()

    def store(self, key: object, value: object):
        """ Stores custom user data. """
        self._user_data.update({key: value})

    def fetch(self, key: object, default=None):
        """ Retrieves the related value from the stored user data. """
        return self._user_data.get(key, default)

    def delete(self, key: object):
        """ Removes an item from the the stored user data. """
        try:
            del self._user_data[key]
        except KeyError:
            pass

    def add(self, requester: int, track: dict):
        """ Adds a track to the queue. """
        self.queue.append(AudioTrack.build(track, requester))

    def add_next(self, requester: int, track: dict):
        """ Adds a track to beginning of the queue """
        self.queue.insert(0, AudioTrack.build(track, requester))

    def add_at(self, index: int, requester: int, track: dict):
        """ Adds a track at a specific index in the queue. """
        self.queue.insert(min(index, len(self.queue) - 1), AudioTrack.build(track, requester))

    async def play(self, track_index: int = 0, ignore_shuffle: bool = False):
        """ Plays the first track in the queue, if any or plays a track from the specified index in the queue. """
        if self.repeat and self.current:
            self.queue.append(self.current)

        self.previous = self.current
        self._prev_position = self.position
        self.current = None
        self.position = 0
        self.paused = False

        if not self.queue:
            await self.stop()
            await self._lavalink.dispatch_event(QueueEndEvent(self))
        else:
            if self.shuffle and not ignore_shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(min(track_index, len(self.queue) - 1))

            self.current = track
            if not self.previous:
                self.previous = self.current
            await self.node.ws.send(op='play', guildId=self.guild_id, track=track.track)
            await self._lavalink.dispatch_event(TrackStartEvent(self, track))

    async def play_now(self, requester: int, track: dict):
        """ Add track and play it. """
        self.add_next(requester, track)
        await self.play(ignore_shuffle=True)

    async def play_at(self, index: int):
        """ Play the queue from a specific point. Disregards tracks before the index. """
        self.queue = self.queue[min(index, len(self.queue) - 1):len(self.queue)]
        await self.play(ignore_shuffle=True)

    async def play_previous(self):
        """ Plays previous track if it exist, if it doesn't raises a NoPreviousTrack error. """
        if not self.previous:
            raise NoPreviousTrack
        self.queue.insert(0, self.previous)
        await self.play(ignore_shuffle=True)

    async def stop(self):
        """ Stops the player, if playing. """
        await self.node.ws.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        """ Plays the next track in the queue, if any. """
        await self.play()

    async def set_pause(self, pause: bool):
        """ Sets the player's paused state. """
        await self.node.ws.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """ Sets the player's volume (150% or 1000% limit imposed by lavalink depending on the version). """
        if self._lavalink._server_version <= 2:
            self.volume = max(min(vol, 150), 0)
        else:
            self.volume = max(min(vol, 1000), 0)
        await self.node.ws.send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def set_gain(self, band: int, gain: float = 0.0):
        """ (Only Lavalink v3.1 or higher) Sets the equalizer band (0-15) gain to the given amount.
        A gain of 0.0 indicates no change. Gain cannot go below -0.25, or exceed 1.0 """
        if not self.node.server_version == 3 and not self.node.ws._is_v31:
            raise UnsupportedLavalinkVersion('Lavalink version must be at least 3.1')
        gain = max(min(gain, 1.0), -0.25)
        band = max(min(band, 15), 0)
        self.equalizer[band] = gain
        await self.node.ws.send(op='equalizer', guildId=self.guild_id, bands=[{'band': band, 'gain': gain}])

    async def set_gains(self, *gain_list):
        """ (Only Lavalink v3.1 or higher) Sets equalizer to the specified values in the list. Must have 15 values. """
        if not self.node.server_version == 3 and not self.node.ws._is_v31:
            raise UnsupportedLavalinkVersion('Lavalink version must be at least 3.1')
        update_package = []
        for value in gain_list:
            if isinstance(value, tuple):
                band = value[0]
                gain = value[1]
            elif isinstance(value, Band):
                band = value.band
                gain = value.gain
            else:
                raise TypeError('only accepts list of tuples or list of Band objects')
            if -1 > value[0] > 15:
                continue
            gain = max(min(float(gain), 1.0), -0.25)
            update_package.append({'band': band, 'gain': gain})
            self.equalizer[band] = gain

        await self.node.ws.send(op='equalizer', guildId=self.guild_id, bands=update_package)

    async def reset_equalizer(self):
        """ (Only Lavalink v3.1 or higher) Resets equalizer to default values. """
        if not self.node.server_version == 3 and not self.node.ws._is_v31:
            raise UnsupportedLavalinkVersion('Lavalink version must be at least 3.1')
        await self.set_gains(*[(x, 0.0) for x in range(15)])

    async def seek(self, pos: int):
        """ Seeks to a given position in the track. """
        await self.node.ws.send(op='seek', guildId=self.guild_id, position=pos)

    async def handle_event(self, event):
        """ Makes the player play the next song from the queue if a song has finished or an issue occurred. """
        if isinstance(event, (TrackStuckEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent) and event.reason == 'FINISHED':
            await self.play()


class PlayerManager:
    def __init__(self, lavalink, player):
        """
        Instantiates a Player Manager.

        :param lavalink:
            Must be a lavalink.Client object.
        :param player:
            Must implement lavalink.BasePlayer.
        """
        if not issubclass(player, BasePlayer):
            raise ValueError('player must implement lavalink.BasePlayer.')

        self.lavalink = lavalink
        self._player = player
        self._players = {}

    def __len__(self):
        return len(self._players)

    def __getitem__(self, item):
        return self._players.get(item, None)

    def __iter__(self):
        """ Returns a tuple of (guild_id, player). """
        for guild_id, player in self._players.items():
            yield guild_id, player

    def __contains__(self, item):
        """ Returns the presence of a player in the cache. """
        return item in self._players

    def find(self, predicate):
        """ Returns the first player in the list based on the given filter predicate. Could be None. """
        found = self.find_all(predicate)
        return found[0] if found else None

    def find_all(self, predicate):
        """ Returns a list of players based on the given filter predicate. """
        return list(filter(predicate, self._players.values()))

    def get(self, guild_id: int, node):
        """ Returns a player from the cache, or creates one if it does not exist. """
        if guild_id not in self._players:
            p = self._player(node=node, lavalink=self.lavalink, guild_id=guild_id)
            self._players[guild_id] = p

        return self._players[guild_id]

    async def remove(self, guild_id: int, call_cleanup: bool = True):
        """ Removes a player from the current players. """
        if guild_id in self._players:
            player = self._players.pop(guild_id)
            if call_cleanup:
                player.cleanup()
            await player.disconnect()

    async def safe_clear(self):
        """ Safely clears all players, by disconnecting them from Discord WS. """
        for player in self._players.values():
            player.cleanup()
            await player.disconnect()
        self._players.clear()

    def clear(self):
        """ Removes all of the players from the cache. """
        self._players.clear()
