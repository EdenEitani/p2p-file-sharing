"""
Tracker server for p2p file sharing.
Manages torrents and peer connections.
"""
from torrent import Torrent
from protocol import *
import asyncio
import json
import sys

class TrackerServer:
    def __init__(self):
        self.next_torrent_id = 0 
        self.torrents = {}  # Mapping of torrent_id to Torrent objects

    def handle_request(self, request) -> dict:
        """Handle incoming client request and return response"""
        operation = request.get(OPC)
        response = {OPC: operation}
        
        if operation == OPT_GET_LIST:
            return self._handle_get_list()
        elif operation == OPT_GET_TORRENT:
            return self._handle_get_torrent(request)
        elif operation == OPT_START_SEED:
            return self._handle_start_seed(request)
        elif operation == OPT_STOP_SEED:
            return self._handle_stop_seed(request)
        elif operation == OPT_UPLOAD_FILE:
            return self._handle_upload_file(request)
        else:
            return {OPC: operation, RET: RET_FAIL}

    def _handle_get_list(self) -> dict:
        """Handle request for list of available torrents"""
        torrent_list = self.get_torrent_list()
        if torrent_list:
            return {
                OPC: OPT_GET_LIST,
                TORRENT_LIST: torrent_list,
                RET: RET_SUCCESS
            }
        return {
            OPC: OPT_GET_LIST,
            RET: RET_NO_AVAILABLE_TORRENTS
        }

    def _handle_get_torrent(self, request) -> dict:
        """Handle request for specific torrent"""
        if request[TID] not in self.torrents:
            return {
                OPC: OPT_GET_TORRENT,
                RET: RET_TORRENT_DOES_NOT_EXIST
            }
        
        torrent_data = self.get_torrent_data(request)
        return {
            OPC: OPT_GET_TORRENT,
            TORRENT: torrent_data,
            RET: RET_SUCCESS
        }

    def _handle_start_seed(self, request) -> dict:
        """Handle request to start seeding"""
        status = self.update_peer_status(request)
        return {
            OPC: OPT_START_SEED,
            RET: status,
            TID: request[TID]
        }

    def _handle_stop_seed(self, request) -> dict:
        """Handle request to stop seeding"""
        status = self.stop_seeding(request)
        return {
            OPC: OPT_STOP_SEED,
            RET: status
        }

    def _handle_upload_file(self, request) -> dict:
        """Handle request to upload new file"""
        status, torrent_id = self.add_new_file(request)
        return {
            OPC: OPT_UPLOAD_FILE,
            RET: status,
            TID: torrent_id
        }

    def get_torrent_list(self) -> list:
        """Get list of all available torrents"""
        return [{
            TID: torrent.tid,
            FILE_NAME: torrent.filename,
            TOTAL_PIECES: torrent.pieces,
            SEEDER_LIST: torrent.get_seeders(),
            LEECHER_LIST: torrent.get_leechers()
        } for torrent in self.torrents.values()]

    def get_torrent_data(self, request: dict) -> dict:
        """Get detailed data for specific torrent"""
        torrent = self.torrents[request[TID]]
        torrent.add_leecher(request[PID], request[IP], request[PORT])
        
        return {
            TID: torrent.tid,
            FILE_NAME: torrent.filename,
            TOTAL_PIECES: torrent.pieces,
            SEEDER_LIST: torrent.get_seeders(),
            LEECHER_LIST: torrent.get_leechers()
        }

    def update_peer_status(self, request: dict) -> int:
        """Update peer status to seeder"""
        if request[TID] not in self.torrents:
            return RET_FAIL
        
        torrent = self.torrents[request[TID]]
        torrent.add_seeder(request[PID], request[IP], request[PORT])
        torrent.remove_leecher(request[PID])
        return RET_SUCCESS

    def stop_seeding(self, request: dict) -> int:
        """Remove peer from seeders list"""
        if request[TID] not in self.torrents:
            return RET_FAIL

        peer_id = request[PID]
        if not peer_id:
            return RET_FAIL

        print(f"[info] removing seeder: {peer_id}")
        self.torrents[request[TID]].remove_seeder(peer_id)
        self.check_seeders(request[TID])
        return RET_SUCCESS

    def check_seeders(self, torrent_id):
        """Remove torrent if it has no seeders"""
        if len(self.torrents[torrent_id].seeders) == 0:
            self.torrents.pop(torrent_id)
            self.next_torrent_id -= 1
            print(f"[info] removed torrent {torrent_id} (no seeders)")

    def add_new_file(self, request: dict) -> tuple[int, int]:
        """Add new file as torrent"""
        # Check if peer is already seeding
        for torrent in self.torrents.values():
            if request[PID] in torrent.get_seeders():
                return RET_ALREADY_SEEDING, -1

        # Create new torrent
        new_torrent = Torrent(
            self.next_torrent_id,
            request[FILE_NAME],
            request[TOTAL_PIECES]
        )
        new_torrent.add_seeder(request[PID], request[IP], request[PORT])
        
        # Add to torrents list
        self.torrents[self.next_torrent_id] = new_torrent
        self.next_torrent_id += 1
        
        return RET_SUCCESS, new_torrent.tid

    async def receive_request(self, reader, writer):
        """Handle incoming connection and request"""
        try:
            data = await reader.read(READ_SIZE)
            request = json.loads(data.decode())
            addr = writer.get_extra_info('peername')

            print(f"[debug] received request from {addr}: {request}")
            
            response = self.handle_request(request)
            payload = json.dumps(response)
            
            print(f"[debug] sending response: {payload}")
            writer.write(payload.encode())
            await writer.drain()

        except Exception as e:
            print(f"[error] {str(e)}")
            print(f"[info] peer disconnected: {writer.get_extra_info('peername')}")
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
        print("[error] invalid port number (must be 0-65535)")
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
        print(f"[error] server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[info] tracker shutdown by user")