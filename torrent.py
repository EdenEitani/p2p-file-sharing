class Torrent:
    def __init__(self, file_name, file_size):
        self.file_name = file_name
        self.file_size = file_size
        self.seeders = []  # List of peers seeding the file
        self.leechers = []  # List of peers downloading the file

    def add_seeder(self, peer_address):
        if peer_address not in self.seeders:
            self.seeders.append(peer_address)

    def add_leecher(self, peer_address):
        if peer_address not in self.leechers:
            self.leechers.append(peer_address)

    def remove_leecher(self, peer_address):
        if peer_address in self.leechers:
            self.leechers.remove(peer_address)

    def get_chunk_count(self, chunk_size):
        """Calculate the number of chunks needed for the file."""
        return (self.file_size + chunk_size - 1) // chunk_size
