class Torrent:
    def __init__(self, file_name, file_size):
        self.file_name = file_name
        self.file_size = file_size
        self.seeders = {}  # {peer_address: set(chunk_ids)}
        self.leechers = set()  # Set of peer addresses
        self.chunk_hashes = {}  # {chunk_id: hash}

    def add_seeder(self, peer_address, chunks):
        self.seeders[peer_address] = set(chunks)
        if peer_address in self.leechers:
            self.leechers.remove(peer_address)

    def add_leecher(self, peer_address):
        if peer_address not in self.seeders:
            self.leechers.add(peer_address)

    def remove_seeder(self, peer_address):
        if peer_address in self.seeders:
            del self.seeders[peer_address]

    def remove_leecher(self, peer_address):
        if peer_address in self.leechers:
            self.leechers.remove(peer_address)

    def get_all_peers(self):
        return list(self.seeders.keys()) + list(self.leechers)
        
    def get_chunk_count(self, chunk_size):
        """Calculate the number of chunks needed for the file."""
        return (self.file_size + chunk_size - 1) // chunk_size
