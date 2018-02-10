from .Player import *


class PlayerManager:
    def __init__(self, bot):
        self.bot = bot
        self._players = {}

    def __len__(self):
        return len(self._players)

    def __getitem__(self, item):
        return self._players.get(item, None)

    def __contains__(self, item):
        return item in self._players

    def find(self, predicate):
        """ Returns the first player in the list based on the given filter predicate. Could be None """
        found = self.find_all(predicate)
        return found[0] if found else None

    def find_all(self, predicate):
        """ Returns a list of players based on the given filter predicate """
        return list(filter(predicate, self._players))

    def get(self, guild_id):
        """ Returns a player from the cache, or creates one if it does not exist """
        if guild_id not in self._players:
            p = Player(bot=self.bot, guild_id=guild_id)
            self._players[guild_id] = p

        return self._players[guild_id]

    def has(self, guild_id) -> bool:
        """ Returns the presence of a player in the cache """
        return guild_id in self._players

    def clear(self):
        """ Removes all of the players from the cache """
        self._players.clear()

    def get_playing(self):
        """ Returns the amount of players that are currently playing """
        return len([p for p in self._players.values() if p.is_playing])

    def use_player(self, player):
        """ Not implemented """
        raise NotImplementedError  # :)
