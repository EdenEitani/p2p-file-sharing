from enum import IntEnum, auto, Enum

class PeerServerOperation(IntEnum):
    GET_LIST = 100
    GET_TORRENT = 110
    START_SEED = 120
    STOP_SEED = 130
    UPLOAD_FILE = 140

class PeerOperation(IntEnum):
    STATUS_INTERESTED = 150
    STATUS_UNINTERESTED = 160
    STATUS_CHOKED = 170
    STATUS_UNCHOKED = 180
    GET_PEERS = 190
    GET_CHUNK = 195

class ReturnCode(IntEnum):
    # Success codes
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    
    # Client error codes
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    
    # Server error codes
    SERVER_ERROR = 500

class PayloadField(str, Enum):
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

# Size constants
READ_SIZE = 24576  # 24KB
CHUNK_SIZE = 16384  # 16KB