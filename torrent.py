from client import Client
from protocol import *

class Torrent:
    def __init__(self, id, file_name, chunks, file_size):
        self.id
        self.file_name = file_name
        self.file_size = file_size
        self.chunks = chunks
        self.seeders = dict()  
        self.leechers = dict()

    def add_seeder(self, seeder: Client):
        seeder = dict()
        seeder['ip'] = seeder.ip
        seeder['port'] = seeder.port
        self.seeders[seeder.id] = seeder
        # if seeder.id in self.leechers:
        #     self.leechers.remove(seeder.id)

    def add_leecher(self, leecher: Client):
        leecher = dict()
        leecher['ip'] = leecher.ip
        leecher['port'] = leecher.port
        self.leechers[leecher.id] = leecher
        # if leecher.id in self.seeders:
        #     self.seeders.remove(leecher.id)

    def remove_seeder(self, id: str):
        if id in self.seeders:
            del self.seeders[id]

    def remove_leecher(self, id: str):
        if id in self.leechers:
            del self.seeders[id]

    def get_seeders(self) -> dict:
        return self.seeders
    
    def get_leechers(self) -> dict:
        return self.leechers
    
    # def get_all_peers(self):
    #     return list(self.seeders.keys()) + list(self.leechers)
        
    # def get_chunk_count(self, chunk_size):
    #     """Calculate the number of chunks needed for the file."""
    #     return (self.file_size + chunk_size - 1) // chunk_size
