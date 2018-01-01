from . import Player


class PlayerManager:
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get(self, guild_id):
        if guild_id not in self.players:
            p = Player(bot=self.bot, guild_id=guild_id)
            self.players[guild_id] = p

        return self.players[guild_id]

    def has(self, guild_id):
        return guild_id in self.players

    def clear():
        self.players.clear()

    def get_playing(self):
        return len([p for p in self.players.values() if p.is_playing()])
