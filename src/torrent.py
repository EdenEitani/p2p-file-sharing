from protocol import PayloadField

class Torrent:
    def __init__(self, id, file_name, num_of_chunks):
        self.id = id
        self.filename = file_name
        self.num_of_chunks = num_of_chunks
        self.seeders = dict()  
        self.leechers = dict()

    def add_seeder(self, id, ip, port):
        seeder = dict()
        seeder[PayloadField.IP_ADDRESS] = ip
        seeder[PayloadField.PORT] = port
        self.seeders[id] = seeder

    def add_leecher(self, id, ip, port):
        leecher = dict()
        leecher[PayloadField.IP_ADDRESS] = ip
        leecher[PayloadField.PORT] = port
        self.leechers[id] = leecher

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
    
    def get_filename(self):
        return self.filename