from enum import IntEnum, auto, Enum

class PeerServerOperation(IntEnum):
    """Operations between peer and server"""
    GET_LIST = 10
    GET_TORRENT = 11
    START_SEED = 12
    STOP_SEED = 13
    UPLOAD_FILE = 14

class PeerOperation(IntEnum):
    """Operations between peers"""
    STATUS_INTERESTED = 1
    STATUS_UNINTERESTED = 2
    STATUS_CHOKED = 3
    STATUS_UNCHOKED = 4
    GET_PEERS = 5
    GET_CHUNK = 6

class ReturnCode(IntEnum):
    """Return codes for operations"""
    FINISHED_SEEDING = 2
    FINISHED_DOWNLOAD = 1
    SUCCESS = 0
    FAIL = -1
    ALREADY_SEEDING = -2
    NO_AVAILABLE_TORRENTS = -3
    TORRENT_DOES_NOT_EXIST = -4

class PayloadField(str, Enum):
    """Payload field names"""
    OPERATION_CODE = 'OPC'
    RETURN_CODE = 'RET'
    IP_ADDRESS = 'IP_ADDRESS'
    PORT = 'PORT'
    PEER_ID = 'PEER_ID'
    TORRENT_ID = 'TORRENT_ID'
    FILE_NAME = 'FILE_NAME'
    NUM_OF_CHUNKS = 'NUM_OF_CHUNKS'
    TORRENT_LIST = 'TORRENT_LIST'
    TORRENT_OBJ = 'TORRENT_OBJ'
    CHUNK_IDX = 'CHUNK_IDX'
    CHUNK_DATA = 'CHUNK_DATA'
    PEER_LIST = 'PEER_LIST'
    SEEDER_LIST = 'SEEDER_LIST'
    LEECHER_LIST = 'LEECHER_LIST'

# Size constants
READ_SIZE = 24576  # 24KB
CHUNK_SIZE = 16384  # 16KB