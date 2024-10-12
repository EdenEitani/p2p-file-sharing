import threading
from collections import defaultdict
import time

class DownloadManager:
    """Handles active downloads, retries, and queuing."""
    
    def __init__(self, max_concurrent_downloads=5):
        self.active_downloads = defaultdict(set)  # {file_name: set(chunk_ids)}
        self.download_queue = []  # [(file_name, chunk_id)]
        self.max_concurrent_downloads = max_concurrent_downloads
        self.lock = threading.Lock()

    def add_download(self, file_name, chunk_id):
        """Add a download to the queue or start it if possible."""
        with self.lock:
            if len(self.active_downloads) < self.max_concurrent_downloads:
                self.active_downloads[file_name].add(chunk_id)
                return True  # Download can start
            else:
                self.download_queue.append((file_name, chunk_id))
                return False  # Download is queued

    def complete_download(self, file_name, chunk_id):
        """Mark a download as completed and start the next one if available."""
        with self.lock:
            self.active_downloads[file_name].remove(chunk_id)
            if not self.active_downloads[file_name]:
                del self.active_downloads[file_name]

            if self.download_queue:
                next_file, next_chunk = self.download_queue.pop(0)
                self.add_download(next_file, next_chunk)  # Start next download

    def retry_download(self, file_name, chunk_id, retries=3):
        """Retry a failed download with a delay."""
        for attempt in range(retries):
            if self.add_download(file_name, chunk_id):
                print(f"Retrying {file_name}, chunk {chunk_id} (Attempt {attempt + 1})")
                return True
            time.sleep(2)  # Small delay before retrying
        print(f"Failed to download {file_name}, chunk {chunk_id} after {retries} attempts.")
        return False
