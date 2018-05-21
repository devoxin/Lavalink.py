class Memory:
    def __init__(self):
        self.reservable = 0
        self.free = 0
        self.used = 0
        self.allocated = 0


class CPU:
    def __init__(self):
        self.cores = 0
        self.system_load = 0.0
        self.lavalink_load = 0.0


class Stats:
    def __init__(self):
        self.playing_players = 0
        self.memory = Memory()
        self.cpu = CPU()
        self.uptime = 0

    def _update(self, data: dict):
        self.playing_players = data.get("playingPlayers", 0)
        self.memory.reservable = data.get("memory", {}).get("reservable", 0)
        self.memory.free = data.get("memory", {}).get("free", 0)
        self.memory.used = data.get("memory", {}).get("used", 0)
        self.memory.allocated = data.get("memory", {}).get("allocated", 0)
        self.cpu.cores = data.get("cpu", {}).get("cores", 0)
        self.cpu.system_load = data.get("cpu", {}).get("systemLoad", 0)
        self.cpu.lavalink_load = data.get("cpu", {}).get("lavalinkLoad", 0)
        self.uptime = data.get("uptime", 0)
