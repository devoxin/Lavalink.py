"""
The majority of this example plugin is based on music.py, except it works with 
hikari and lightbulb Discord libraries.
"""
import re
import logging
import hikari
import lightbulb
import lavalink

plugin = lightbulb.Plugin('Music', 'Music commands')

class EventHandler:
    """Events from the Lavalink server"""

    @lavalink.listener(lavalink.TrackStartEvent)
    async def track_start(self, event: lavalink.TrackStartEvent):
        logging.info('Track started on guild: %s', event.player.guild_id)

    @lavalink.listener(lavalink.TrackEndEvent)
    async def track_end(self, event: lavalink.TrackEndEvent):
        logging.info('Track finished on guild: %s', event.player.guild_id)

    @lavalink.listener(lavalink.TrackExceptionEvent)
    async def track_exception(self, event: lavalink.TrackExceptionEvent):
        logging.warning('Track exception event happened on guild: %d', event.player.guild_id)

    @lavalink.listener(lavalink.QueueEndEvent)
    async def queue_finish(self, event: lavalink.QueueEndEvent):
        logging.info('Queue finished on guild: %s', event.player.guild_id)


@plugin.listener(hikari.ShardReadyEvent)
async def init(event: hikari.ShardReadyEvent) -> None:
    """Add node to bot on ready"""

    client = lavalink.Client(plugin.bot.get_me().id)
    client.add_node(
        host='localhost',
        port=2333,
        password='youshallnotpass',
        region='us',
        name='default-node'
    )

    client.add_event_hooks(EventHandler())
    plugin.bot.d.lavalink = client


@plugin.listener(hikari.VoiceServerUpdateEvent)
async def voice_server_update(event: hikari.VoiceServerUpdateEvent) -> None:
    # the data needs to be transformed before being handed down to
    # voice_update_handler
    lavalink_data = {
        't': 'VOICE_SERVER_UPDATE',
        'd': {
            'guild_id': event.guild_id,
            'endpoint': event.endpoint[6:],  # get rid of wss://
            'token': event.token,
        }
    }
    await plugin.bot.d.lavalink.voice_update_handler(lavalink_data)

@plugin.listener(hikari.VoiceStateUpdateEvent)
async def voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:
    # the data needs to be transformed before being handed down to
    # voice_update_handler
    lavalink_data = {
        't': 'VOICE_STATE_UPDATE',
        'd': {
            'guild_id': event.state.guild_id,
            'user_id': event.state.user_id,
            'channel_id': event.state.channel_id,
            'session_id': event.state.session_id,
        }
    }
    await plugin.bot.d.lavalink.voice_update_handler(lavalink_data)

async def _join(ctx: lightbulb.Context):
    states = plugin.bot.cache.get_voice_states_view_for_guild(ctx.guild_id)
    voice_state = [state[1] for state in filter(lambda i : i[0] == ctx.author.id, states.items())]

    # user not in voice channel
    if not voice_state:
        return
    
    channel_id = voice_state[0].channel_id  # channel user is connected to
    plugin.bot.d.lavalink.player_manager.create(guild_id=ctx.guild_id)
    await plugin.bot.update_voice_state(ctx.guild_id, channel_id, self_deaf=True)
    
    return channel_id


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command('join', 'Joins the voice channel you are in.', auto_defer=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def join(ctx: lightbulb.Context) -> None:
    """
        Connect the bot to the voice channel the user is currently in 
        and create a player_manager if it doesn't exist yet.
    """

    channel_id = await _join(ctx)
    if not channel_id:
        await ctx.respond('Connect to a voice channel first!')
        return
    
    await ctx.respond(f'Connected to <#{channel_id}>')
    logging.info('Client connected to voice channel on guild: %s', ctx.guild_id)


@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.command('leave', 'Leaves voice channel, clearing queue.', auto_defer=True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def leave(ctx: lightbulb.Context) -> None:
    """Leaves the voice channel the bot is in, clearing the queue."""

    player = plugin.bot.d.lavalink.player_manager.get(ctx.guild_id)
    
    if not player or not player.is_connected:
        await ctx.respond('Not currently in any voice channel!')
        return

    player.queue.clear()  # clear queue
    await player.stop()  # stop player
    player.channel_id = None  # update the channel_id of the player to None
    await plugin.bot.update_voice_state(ctx.guild_id, None)
    await ctx.respond('Disconnected')
    

@plugin.command()
@lightbulb.add_checks(lightbulb.guild_only)
@lightbulb.option('query', 'The query to search for.', modifier=lightbulb.OptionModifier.CONSUME_REST, required=True)
@lightbulb.command('play', 'Searches query on youtube, or adds the URL to the queue.', auto_defer = True)
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def play(ctx: lightbulb.Context) -> None:
    """Searches the query on youtube, or adds the URL to the queue."""

    player = plugin.bot.d.lavalink.player_manager.get(ctx.guild_id)
    # Remove leading and trailing <>. <> may be used to suppress embedding links in Discord.
    query = ctx.options.query.strip('<>')
    
    if not player or not player.is_connected:
        channel_id = await _join(ctx)
        if not channel_id:
            await ctx.respond('Connect to a voice channel first!')
            return
    
    # get player again after having connected to voice channel
    player = plugin.bot.d.lavalink.player_manager.get(ctx.guild_id)

    # Check if the user input might be a URL. If it isn't, we can Lavalink do a YouTube search for it instead.
    url_rx = re.compile(r'https?://(?:www\.)?.+')
    if not url_rx.match(query):
        query = f'ytsearch:{query}'

    # Get the results for the query from Lavalink.
    results = await player.node.get_tracks(query)

    # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
    # Alternatively, results.tracks could be an empty array if the query yielded no tracks.
    if not results or not results.tracks:
        return await ctx.respond('Nothing found!')

    embed = hikari.Embed()

    if results.load_type == 'PLAYLIST_LOADED':
        tracks = results.tracks

        for track in tracks:
            # Add all of the tracks from the playlist to the queue.
            player.add(requester=ctx.author.id, track=track)

        embed.title = 'Playlist Enqueued!'
        embed.description = f'{results.playlist_info.name} - {len(tracks)} tracks'
    else:
        track = results.tracks[0]
        embed.title = 'Track Enqueued'
        embed.description = f'[{track.title}]({track.uri})'

        player.add(requester=ctx.author.id, track=track)

    await ctx.respond(embed=embed)

    # We don't want to call .play() if the player is playing as that will effectively skip
    # the current track.
    if not player.is_playing:
        await player.play()


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
