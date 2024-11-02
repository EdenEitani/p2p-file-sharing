class Chunk:
    """
    Represents a chunk of a file with index and data
    """
    def __init__(self, index: int, data):
        self.index = index
        self.data = data

class ChunkBuffer:
    """
    Manages chunks of a file during download/upload
    """
    def __init__(self):
        self._buffer = []
        self._size = 0
        self._have_chunks = []

    def get_buffer(self):
        return self._buffer

    def set_buffer(self, length: int):
        """
        Initialize buffer of given length
        """
        self._buffer = [0] * length
        self._size = length
        self._have_chunks = [False] * length

    def add_data(self, chunk: Chunk) -> int:
        """
        Add chunk data to buffer
        """
        idx = chunk.index
        if 0 <= idx < self._size:
            self._buffer[idx] = chunk.data
            self._have_chunks[idx] = True
            return 1
        return -1

    def get_data(self, idx: int):
        """
        Get chunk data at index
        """
        if 0 <= idx < self._size and self._buffer[idx] != 0:
            return self._buffer[idx]
        return -1
            
    def get_size(self) -> int:
        return self._size

    def get_missing_chunks(self) -> list:
        return [idx for idx, have in enumerate(self._have_chunks) if not have]

    def has_chunk(self, idx: int) -> bool:
        return self._have_chunks[idx]

    @property
    def has_all_chunks(self) -> bool:
        return all(self._have_chunks)
