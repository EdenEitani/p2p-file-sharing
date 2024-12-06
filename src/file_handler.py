import os
import hashlib
from protocol import CHUNK_SIZE
import base64

def encode_file(file_name:str):
    chunks = [] 
    with open(file_name, 'rb') as f:
        chunk = f.read(CHUNK_SIZE)
        while chunk:
            chunks.append(base64.b64encode(chunk).decode('utf-8'))
            chunk = f.read(CHUNK_SIZE)
    return len(chunks), chunks

def decode_file(chunks:list, path):
    with open(path, 'wb') as f:
        for chunk in chunks:
            f.write(base64.b64decode(chunk.encode('utf-8')))

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
        chunk_hashes = {}

        file_size = os.path.getsize(file_path)

        # If the file is smaller than or equal to the chunk size, no splitting is needed
        if file_size <= CHUNK_SIZE:
            print(f"{file_path} is smaller than or equal to {CHUNK_SIZE} bytes. No splitting needed.")
            chunk_hashes[0] = FileHandler.calculate_hash(file_path)
            return chunk_hashes

        # If the file is larger, split it into chunks
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
        if not os.path.exists(chunk_filename):
            return False
        return FileHandler.calculate_hash(chunk_filename) == expected_hash

    @staticmethod
    def chunk_exists(chunk_id, file_name, expected_hash):
        """
        Check if a chunk already exists and matches the expected hash.
        Returns True if the chunk exists and is valid, otherwise False.
        """
        chunk_filename = f"{file_name}_chunk_{chunk_id}"
        if os.path.exists(chunk_filename):
            is_valid = FileHandler.verify_chunk(chunk_id, file_name, expected_hash)
            if is_valid:
                print(f"Chunk {chunk_id} of {file_name} already exists and is valid.")
            else:
                print(f"Chunk {chunk_id} of {file_name} exists but is corrupted.")
            return is_valid
        print(f"Chunk {chunk_id} of {file_name} does not exist.")
        return False
