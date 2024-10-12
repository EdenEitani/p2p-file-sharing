import os
import hashlib

CHUNK_SIZE = 512 * 1024  # 512 KB

class FileHandler:
    @staticmethod
    def calculate_hash(file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def split_file(file_path):
        """Split the file into chunks and return a dictionary of chunk hashes."""
        chunk_hashes = {}
        with open(file_path, 'rb') as f:
            chunk_number = 0
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                chunk_filename = f"{file_path}_chunk_{chunk_number}"
                with open(chunk_filename, 'wb') as chunk_file:
                    chunk_file.write(chunk)

                chunk_hashes[chunk_number] = FileHandler.calculate_hash(chunk_filename)
                chunk_number += 1
        print(f"{file_path} split into {chunk_number} chunks.")
        return chunk_hashes

    @staticmethod
    def combine_chunks(file_name, chunk_count, destination):
        """Combine all chunks into the original file."""
        with open(os.path.join(destination, file_name), 'wb') as output_file:
            for i in range(chunk_count):
                chunk_filename = f"{file_name}_chunk_{i}"
                with open(chunk_filename, 'rb') as chunk_file:
                    output_file.write(chunk_file.read())

    @staticmethod
    def verify_chunk(chunk_id, file_name, expected_hash):
        chunk_filename = f"{file_name}_chunk_{chunk_id}"
        return FileHandler.calculate_hash(chunk_filename) == expected_hash
