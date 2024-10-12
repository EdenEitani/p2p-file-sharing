# defines the PEER2PEER protocol and PEER2SERVER protocol.

# PEER 2 SERVER         
OPT_GET_LIST = 10
OPT_GET_TORRENT = 11
OPT_START_SEED = 12
OPT_STOP_SEED = 13
OPT_UPLOAD_FILE = 14

RET_FINSH_SEEDING = 2
RET_FINISHED_DOWNLOAD = 1
RET_SUCCESS = 0
RET_FAIL = -1
RET_ALREADY_SEEDING = -2
RET_NO_AVAILABLE_TORRENTS = -3
RET_TORRENT_DOES_NOT_EXIST = -4

# PEER 2 PEER
OPT_STATUS_INTERESTED = 1
OPT_STATUS_UNINTERESTED = 2
OPT_STATUS_CHOKED = 3
OPT_STATUS_UNCHOKED = 4
OPT_GET_PEERS = 5
OPT_GET_CHUNK = 6

# PAYLOAD FIELD NAMES
OPC = 'OPC'
RET = 'RET'
IP = 'IP_ADDRESS'
PORT = 'PORT'
PID = 'PEER_ID'
TID = 'TORRENT_ID'
FILE_NAME = 'FILE_NAME'
TOTAL_CHUNKS = 'NUM_OF_CHUNKS'
TORRENT_LIST = 'TORRENT_LIST'
TORRENT = 'TORRENT_OBJ'
CHUNK_IDX = 'CHUNK_IDX'
CHUNK_DATA = 'CHUNK_DATA'
PEER_LIST = 'PEER_LIST'
SEEDER_LIST = 'SEEDER_LIST'
LEECHER_LIST = 'LEECHER_LIST'

# SIZE CONSTANTS - (24KB / 16KB)
READ_SIZE = 24576
CHUNK_SIZE = 16384