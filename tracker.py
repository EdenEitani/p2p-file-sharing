from flask import Flask, request, jsonify
from torrent import Torrent

class Tracker:
    def __init__(self):
        self.torrents = {}  # {file_name: Torrent}
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/register', methods=['POST'])
        def register_peer():
            """Register a peer based on the presence of chunk data."""
            data = request.json
            file_name = data['file_name']
            peer_address = f"{data['ip']}:{data['port']}"
            chunks = data.get('chunks', [])

            if file_name not in self.torrents:
                # Create a new torrent if it doesn't exist
                self.torrents[file_name] = Torrent(file_name, 0)

            torrent = self.torrents[file_name]

            if chunks:
                # If chunks are provided, register as seeder
                torrent.add_seeder(peer_address, chunks)
            else:
                # Otherwise, register as leecher
                torrent.add_leecher(peer_address)

            return "Peer registered successfully", 200

        @self.app.route('/peers', methods=['GET'])
        def get_peers():
            """Get the list of seeders for a specific file."""
            file_name = request.args.get('file')
            if file_name in self.torrents:
                # Convert the set of seeders to a list before serializing
                seeders_list = list(self.torrents[file_name].seeders)
                return jsonify(seeders_list), 200
            return "File not found", 404


        @self.app.route('/chunks', methods=['GET'])
        def get_chunk_info():
            """Return chunk hashes for the requested file."""
            file_name = request.args.get('file')
            torrent = self.torrents.get(file_name)
            print(f"File requested for download: {torrent.file_name} with available hashes: {torrent.chunk_hashes}")
            if torrent:
                return jsonify(torrent.chunk_hashes), 200
            return "File not found", 404
        
        @self.app.route('/available_files', methods=['GET'])
        def available_files():
            """Return the list of available files."""
            return jsonify(list(self.torrents.keys()))

    def run(self):
        self.app.run(host='0.0.0.0', port=8000)


if __name__ == '__main__':
    tracker = Tracker()
    tracker.run()
