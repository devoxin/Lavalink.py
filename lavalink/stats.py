class Penalty:
    def __init__(self, stats):
        self.player_penalty = stats.playing_players
        self.cpu_penalty = 1.05 ** (100 * stats.system_load) * 10 - 10
        self.null_frame_penalty = 0
        self.deficit_frame_penalty = 0

        if stats.frames_nulled is not -1:
            self.null_frame_penalty = (1.03 ** (500 * (stats.frames_nulled / 3000))) * 300 - 300
            self.null_frame_penalty *= 2

        if stats.frames_deficit is not -1:
            self.deficit_frame_penalty = (1.03 ** (500 * (stats.frames_deficit / 3000))) * 600 - 600

        self.total = self.player_penalty + self.cpu_penalty + self.null_frame_penalty + self.deficit_frame_penalty


class Stats:
    def __init__(self, node, data):
        self._node = node

        self.uptime = data['uptime']

        self.players = data['players']
        self.playing_players = data['playingPlayers']

        memory = data['memory']
        self.memory_free = memory['free']
        self.memory_used = memory['used']
        self.memory_allocated = memory['allocated']
        self.memory_reservable = memory['reservable']

        cpu = data['cpu']
        self.cpu_cores = cpu['cores']
        self.system_load = cpu['systemLoad']
        self.lavalink_load = cpu['lavalinkLoad']

        frame_stats = data.get('frameStats', {})
        self.frames_sent = frame_stats.get('sent', -1)
        self.frames_nulled = frame_stats.get('nulled', -1)
        self.frames_deficit = frame_stats.get('deficit', -1)
        self.penalty = Penalty(self)
