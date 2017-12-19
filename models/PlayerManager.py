from . import Player


class PlayerManager:
    def __init__(self, bot):
        bot = bot
        players = {}

    def get(self, guild_id):
        if guild_id not in players:
            p = Player(bot=bot, guild_id=guild_id)
            players[guild_id] = p

        return players[guild_id]

    def get_playing(self):
        return len([p for p in players.values() if p.is_playing()])
