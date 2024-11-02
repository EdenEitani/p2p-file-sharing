from client import Client
from protocol import *

class Torrent:
    def __init__(self, id, file_name, num_of_chunks):
        self.id = id
        self.file_name = file_name
        self.num_of_chunks = num_of_chunks
        self.seeders = dict()  
        self.leechers = dict()

    def add_seeder(self, id, ip, port):
        seeder = dict()
        seeder[IP] = ip
        seeder[PORT] = port
        self.seeders[id] = seeder
        # if seeder.id in self.leechers:
        #     self.leechers.remove(seeder.id)

    def add_leecher(self, id, ip, port):
        leecher = dict()
        leecher[IP] = ip
        leecher[PORT] = port
        self.leechers[id] = leecher
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
