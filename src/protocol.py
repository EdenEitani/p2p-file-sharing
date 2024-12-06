from enum import IntEnum, auto, Enum

class PeerServerOperation(IntEnum):
    """Operations between peer and server"""
    GET_LIST = 100
    GET_TORRENT = 110
    START_SEED = 120
    STOP_SEED = 130
    UPLOAD_FILE = 140

class PeerOperation(IntEnum):
    """Operations between peers"""
    STATUS_INTERESTED = 150
    STATUS_UNINTERESTED = 160
    STATUS_CHOKED = 170
    STATUS_UNCHOKED = 180
    GET_PEERS = 190
    GET_CHUNK = 195

class ReturnCode(IntEnum):
    # Success codes (200-299)
    SUCCESS = 200
    FINISHED_DOWNLOAD = 201
    FINISHED_SEEDING = 202
    
    # Client errors (400-499)
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    ALREADY_SEEDING = 409
    NO_AVAILABLE_TORRENTS = 410
    TORRENT_DOES_NOT_EXIST = 411
    FAIL = 450
    FAILED_TO_DOWNLOAD = 451

class PayloadField(str, Enum):
    """Payload field names"""
    OPERATION_CODE = 'OP_CODE'
    RETURN_CODE = 'RET_CODE'
    IP_ADDRESS = 'IP_ADDRESS'
    PORT = 'PORT'
    PEER_ID = 'PEER_ID'
    TORRENT_ID = 'TORRENT_ID'
    FILE_NAME = 'FILE_NAME'
    NUM_OF_CHUNKS = 'NUM_OF_CHUNKS'
    TORRENT_LIST = 'TORRENT_LIST'
    TORRENT_OBJECT = 'TORRENT_OBJECT'
    CHUNK_IDX = 'CHUNK_INDX'
    CHUNK_DATA = 'CHUNK_DATA'
    PEER_LIST = 'PEER_LIST'
    SEEDER_LIST = 'SEEDER_LIST'
    LEECHER_LIST = 'LEECHER_LIST'

READ_SIZE = 24576  # 24KB
CHUNK_SIZE = 16384  # 16KB