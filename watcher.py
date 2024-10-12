import os
import time

class Watcher:
    def __init__(self, peer, folder_to_watch):
        self.peer = peer
        self.folder_to_watch = folder_to_watch
        self.registered_files = set()

    def watch_folder(self):
        while True:
            files = os.listdir(self.folder_to_watch)
            for file_name in files:
                file_path = os.path.join(self.folder_to_watch, file_name)
                if os.path.isfile(file_path) and file_name not in self.registered_files:
                    print(f"New file detected: {file_name}")
                    self.peer.file_name = file_path
                    chunks = self.peer.split_file()
                    self.peer.register_with_tracker()
                    self.registered_files.add(file_name)
            time.sleep(5)  # Check for new files every 5 seconds