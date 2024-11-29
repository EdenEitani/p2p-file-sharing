"""
Tracker server for p2p file sharing.
Manages torrents and peer connections.
"""
from torrent import Torrent
from protocol import PeerServerOperation, ReturnCode, PayloadField, READ_SIZE
import asyncio
import json
import sys
from logger import setup_logger

logger = setup_logger()

class TrackerServer:
    def __init__(self):
        self.next_torrent_id = 0 
        self.torrents = {}  # Mapping of torrent_id to Torrent objects

    def handle_request(self, request) -> dict:
        """Handle incoming client request and return response"""
        operation = request.get(PayloadField.OPERATION_CODE)
        response = {PayloadField.OPERATION_CODE: operation}
        
        if operation == PeerServerOperation.GET_LIST:
            return self._handle_get_list()
        elif operation == PeerServerOperation.GET_TORRENT:
            return self._handle_get_torrent(request)
        elif operation == PeerServerOperation.START_SEED:
            return self._handle_start_seed(request)
        elif operation == PeerServerOperation.STOP_SEED:
            return self._handle_stop_seed(request)
        elif operation == PeerServerOperation.UPLOAD_FILE:
            return self._handle_upload_file(request)
        else:
            return {PayloadField.OPERATION_CODE: operation, PayloadField.RETURN_CODE: ReturnCode.FAIL}

    def _handle_get_list(self) -> dict:
        """Handle request for list of available torrents"""
        torrent_list = self.get_torrent_list()
        if torrent_list:
            return {
                PayloadField.OPERATION_CODE: PeerServerOperation.GET_LIST,
                PayloadField.TORRENT_LIST: torrent_list,
                PayloadField.RETURN_CODE: ReturnCode.SUCCESS
            }
        return {
            PayloadField.OPERATION_CODE: PeerServerOperation.GET_LIST,
            PayloadField.RETURN_CODE: ReturnCode.NO_AVAILABLE_TORRENTS
        }

    def _handle_get_torrent(self, request) -> dict:
        """Handle request for specific torrent"""
        if request[PayloadField.TORRENT_ID] not in self.torrents:
            return {
                PayloadField.OPERATION_CODE: PeerServerOperation.GET_TORRENT,
                PayloadField.RETURN_CODE: ReturnCode.TORRENT_DOES_NOT_EXIST
            }
        
        torrent_data = self.get_torrent_data(request)
        return {
            PayloadField.OPERATION_CODE: PeerServerOperation.GET_TORRENT,
            PayloadField.TORRENT_OBJ: torrent_data,
            PayloadField.RETURN_CODE: ReturnCode.SUCCESS
        }

    def _handle_start_seed(self, request) -> dict:
        """Handle request to start seeding"""
        status = self.update_peer_status(request)
        return {
            PayloadField.OPERATION_CODE: PeerServerOperation.START_SEED,
            PayloadField.RETURN_CODE: status,
            PayloadField.TORRENT_ID: request[PayloadField.TORRENT_ID]
        }

    def _handle_stop_seed(self, request) -> dict:
        """Handle request to stop seeding"""
        status = self.stop_seeding(request)
        return {
            PayloadField.OPERATION_CODE: PeerServerOperation.STOP_SEED,
            PayloadField.RETURN_CODE: status
        }

    def _handle_upload_file(self, request) -> dict:
        """Handle request to upload new file"""
        status, torrent_id = self.add_new_file(request)
        return {
            PayloadField.OPERATION_CODE: PeerServerOperation.UPLOAD_FILE,
            PayloadField.RETURN_CODE: status,
            PayloadField.TORRENT_ID: torrent_id
        }

    def get_torrent_list(self) -> list:
        """Get list of all available torrents"""
        return [{
            PayloadField.TORRENT_ID: torrent.id,
            PayloadField.FILE_NAME: torrent.filename,
            PayloadField.NUM_OF_CHUNKS: torrent.num_of_chunks,
            PayloadField.SEEDER_LIST: torrent.get_seeders(),
            PayloadField.LEECHER_LIST: torrent.get_leechers()
        } for torrent in self.torrents.values()]

    def get_torrent_data(self, request: dict) -> dict:
        """Get detailed data for specific torrent"""
        torrent = self.torrents[request[PayloadField.TORRENT_ID]]
        torrent.add_leecher(request[PayloadField.PEER_ID], request[PayloadField.IP_ADDRESS], request[PayloadField.PORT])
        
        return {
            PayloadField.TORRENT_ID: torrent.id,
            PayloadField.FILE_NAME: torrent.filename,
            PayloadField.NUM_OF_CHUNKS: torrent.num_of_chunks,
            PayloadField.SEEDER_LIST: torrent.get_seeders(),
            PayloadField.LEECHER_LIST: torrent.get_leechers()
        }

    def update_peer_status(self, request: dict) -> int:
        """Update peer status to seeder"""
        if request[PayloadField.TORRENT_ID] not in self.torrents:
            return ReturnCode.FAIL
        
        torrent = self.torrents[request[PayloadField.TORRENT_ID]]
        torrent.add_seeder(request[PayloadField.PEER_ID], request[PayloadField.IP_ADDRESS], request[PayloadField.PORT])
        torrent.remove_leecher(request[PayloadField.PEER_ID])
        return ReturnCode.SUCCESS

    def stop_seeding(self, request: dict) -> int:
        """Remove peer from seeders list"""
        if request[PayloadField.TORRENT_ID] not in self.torrents:
            return ReturnCode.FAIL

        peer_id = request[PayloadField.PEER_ID]
        if not peer_id:
            return ReturnCode.FAIL

        logger.info(f"removing seeder: {peer_id}")
        self.torrents[request[PayloadField.TORRENT_ID]].remove_seeder(peer_id)
        self.check_seeders(request[PayloadField.TORRENT_ID])
        return ReturnCode.SUCCESS

    def check_seeders(self, torrent_id):
        """Remove torrent if it has no seeders"""
        if len(self.torrents[torrent_id].seeders) == 0:
            self.torrents.pop(torrent_id)
            self.next_torrent_id -= 1
            logger.info(f"removed torrent {torrent_id} (no seeders)")

    def add_new_file(self, request: dict) -> tuple[int, int]:
        """Add new file as torrent"""
        # Check if peer is already seeding
        for torrent in self.torrents.values():
            if request[PayloadField.PEER_ID] in torrent.get_seeders():
                return ReturnCode.ALREADY_SEEDING, -1

        # Create new torrent
        new_torrent = Torrent(
            self.next_torrent_id,
            request[PayloadField.FILE_NAME],
            request[PayloadField.NUM_OF_CHUNKS]
        )
        new_torrent.add_seeder(request[PayloadField.PEER_ID], request[PayloadField.IP_ADDRESS], request[PayloadField.PORT])
        
        # Add to torrents list
        self.torrents[self.next_torrent_id] = new_torrent
        self.next_torrent_id += 1
        
        return ReturnCode.SUCCESS, new_torrent.id

    async def receive_request(self, reader, writer):
        """Handle incoming connection and request"""
        try:
            data = await reader.read(READ_SIZE)
            request = json.loads(data.decode())
            addr = writer.get_extra_info('peername')

            logger.debug(f"received request from {addr}: {request}")
            
            response = self.handle_request(request)
            payload = json.dumps(response)
            
            logger.debug(f"sending response: {payload}")
            writer.write(payload.encode())
            await writer.drain()

        except Exception as e:
            logger.error(f"{str(e)}")
            logger.info(f"peer disconnected: {writer.get_extra_info('peername')}")
        finally:
            writer.close()

def validate_port(port: str) -> bool:
    """Validate port number"""
    try:
        port_num = int(port)
        return 0 <= port_num <= 65535
    except ValueError:
        return False

def parse_arguments() -> str:
    """Parse command line arguments"""
    args = len(sys.argv) - 1

    if args == 0:
        return None
    
    if args == 1:
        port = sys.argv[1]
        if validate_port(port):
            return port
        logger.error("invalid port number (must be 0-65535)")
        return None

    print("Usage: tracker.py [server port]")
    print("Using default port")
    return None

async def main():
    """Main entry point"""
    try:
        ip = asyncio.streams.socket.gethostbyname(asyncio.streams.socket.gethostname())
        port = parse_arguments() or 8888
            
        tracker = TrackerServer()
        server = await asyncio.start_server(tracker.receive_request, ip, port)
        addr = server.sockets[0].getsockname()
        print(f'[info] tracker serving on {addr}')

        async with server:
            await server.serve_forever()
    
    except Exception as e:
        logger.error(f"server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[info] tracker shutdown by user")