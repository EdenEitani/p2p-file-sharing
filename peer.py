import socket
import requests
import os
import threading
import tqdm
from file_handler import FileHandler
from download_manager import DownloadManager
import sys
from time import time

TRACKER_URL = 'http://tracker:8000'
CHUNK_SIZE = 512 * 1024  # 512 KB

class Peer:
    def __init__(self, peer_ip, peer_port, shared_files_path, download_path):
        self.peer_ip = peer_ip
        self.peer_port = int(peer_port)
        self.shared_files_path = shared_files_path
        self.download_path = download_path
        self.available_chunks = {}  # {file_name: set(chunk_ids)}
        self.chunk_hashes = {}  # {file_name: {chunk_id: expected_hash}}
        self.download_manager = DownloadManager(max_concurrent_downloads=5)

    def start_peer(self):
        """Register files, start the peer server, and wait for user input."""
        self.register_all_files()
        threading.Thread(target=self.start_server, daemon=True).start()
        self.download_all_files() # Test

    def register_all_files(self):
        """Register all available files with the tracker."""
        for file_name in os.listdir(self.shared_files_path):
            file_path = os.path.join(self.shared_files_path, file_name)
            if os.path.isfile(file_path):
                print(f"Registering {file_name} as a seeder...")
                chunk_hashes = FileHandler.split_file(file_path)
                self.available_chunks[file_name] = set(chunk_hashes.keys())
                self.register_with_tracker(file_name, chunk_hashes)

    def register_with_tracker(self, file_name, chunk_hashes):
        """Register a file with the tracker."""
        data = {
            'ip': self.peer_ip,
            'port': self.peer_port,
            'file_name': file_name,
            'chunks': list(chunk_hashes.keys())
        }
        response = requests.post(f"{TRACKER_URL}/register", json=data)
        print(f"Registered {file_name} with tracker: {response.text}")

    def start_server(self):
        """Start the peer server to handle chunk requests."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', self.peer_port))
        server.listen(5)
        print(f"Peer server running on port {self.peer_port}...")

        while True:
            conn, addr = server.accept()
            threading.Thread(target=self.handle_peer_connection, args=(conn, addr), daemon=True).start()

    def handle_peer_connection(self, conn, addr):
        """Respond to chunk requests."""
        try:
            data = conn.recv(1024).decode('utf-8')
            file_name, chunk_id = data.split(":")
            chunk_id = int(chunk_id)
            chunk_path = f"{file_name}_chunk_{chunk_id}"

            if os.path.exists(chunk_path):
                with open(chunk_path, 'rb') as chunk_file:
                    conn.sendall(chunk_file.read())
            else:
                conn.sendall(b'ERROR: Chunk not found.')
        except Exception as e:
            print(f"Error handling peer connection: {e}")
        finally:
            conn.close()

    def wait_for_user_input(self):
        """Wait for user input to initiate downloads or exit."""
        while True:
            try:
                file_name = input("\nEnter the name of the file to download (or 'exit' to quit): ")
                if file_name.lower() == 'exit':
                    print("Exiting...")
                    break
                elif file_name:
                    self.download_file(file_name)
            except EOFError:
                print("Cought an error, Exiting...")
                break
            
    def get_available_files(self):
        """Fetch the list of available files from the tracker."""
        try:
            response = requests.get(f"{TRACKER_URL}/available_files")
            if response.status_code == 200:
                return response.json()  # List of available file names
            else:
                print(f"Failed to fetch available files: {response.status_code}")
                return []
        except requests.RequestException as e:
            print(f"Error contacting tracker: {e}")
            return []

    
    def download_all_files(self):
        """download available files without user input."""
        available_files = self.get_available_files()
        print(f"Available files to download: {available_files}")
        for file_name in available_files:
            try:
                print(f"Attempting to download: {file_name}")
                self.download_file(file_name)
            except Exception as e:
                print(f"Error in download loop: {e}")


    def download_file(self, file_name):
        """Download a file from other peers."""
        peers = requests.get(f"{TRACKER_URL}/peers", params={'file': file_name}).json()
        self.chunk_hashes[file_name] = requests.get(
            f"{TRACKER_URL}/chunks", params={'file': file_name}).json()

        chunk_count = len(self.chunk_hashes[file_name])
        with tqdm.tqdm(total=chunk_count, unit='chunk') as pbar:
            for chunk_id in range(chunk_count):
                if chunk_id not in self.available_chunks.setdefault(file_name, set()):
                    if not self.download_manager.add_download(file_name, chunk_id):
                        continue

                    success = self.request_chunk_from_peers(file_name, chunk_id, peers)
                    if success:
                        self.available_chunks[file_name].add(chunk_id)
                        pbar.update(1)
                        self.download_manager.complete_download(file_name, chunk_id)

        print(f"Reassembling {file_name}...")
        FileHandler.combine_chunks(file_name, chunk_count, self.download_path)

    def request_chunk_from_peers(self, file_name, chunk_id, peers):
        """Attempt to download a chunk from available peers."""
        for peer in peers:
            peer_ip, peer_port = peer.split(":")
            if self.request_chunk(file_name, chunk_id, peer_ip, int(peer_port)):
                return True
        print(f"Chunk {chunk_id} not found.")
        return False

    def request_chunk(self, file_name, chunk_id, peer_ip, peer_port):
        """Connect to a peer and request a chunk."""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((peer_ip, peer_port))
            client.sendall(f"{file_name}:{chunk_id}".encode('utf-8'))

            # Open the chunk file for writing the received data
            chunk_filename = f"{file_name}_chunk_{chunk_id}"
            with open(chunk_filename, 'wb') as chunk_file:
                while True:
                    data = client.recv(CHUNK_SIZE)
                    if not data:
                        break  # End of data stream
                    chunk_file.write(data)  # Write received data to the chunk file

            client.close()

            # Verify the chunk integrity after receiving the data
            if FileHandler.verify_chunk(chunk_id, file_name, self.chunk_hashes[file_name][str(chunk_id)]):
                print(f"Chunk {chunk_id} of {file_name} received and verified.")
                self.available_chunks.setdefault(file_name, set()).add(chunk_id)
                return True
            else:
                print(f"Chunk {chunk_id} of {file_name} is corrupted.")
                return False

        except Exception as e:
            print(f"Error requesting chunk {chunk_id} from {peer_ip}:{peer_port} - {e}")
            return False


if __name__ == "__main__":
    # Ensure the correct number of command-line arguments are provided
    if len(sys.argv) != 5:
        print("Usage: python peer.py <peer_ip> <peer_port> <shared_files_path> <download_path>")
        sys.exit(1)

    # Extract command-line arguments
    peer_ip, peer_port, shared_files_path, download_path = sys.argv[1:]

    # Initialize and start the peer
    peer = Peer(peer_ip, peer_port, shared_files_path, download_path)
    peer.start_peer()

