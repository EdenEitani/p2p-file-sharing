"""
Client functionality and actions for p2p file sharing.
"""
import hashlib
import asyncio
import sys
import json
from socket import *
from protocol import *
import file_handler as fh
from chunk import Chunk

class State:
    def __init__(self):
        self.seeding = False
        self.leeching = False
        self.choked = True
        self.interested = False

class ClientHelper:
    """
    Helper class that handles file operations and peer selection
    """
    def __init__(self, client):
        self.client = client

    async def distribute_chunks_evenly(self, num_chunks: int):
        """
        Distribute chunk requests evenly among available peers
        """
        num_peers = len(self.client.seeder_list)
        peer_list = list(self.client.seeder_list.values())
        request_list = [self.client.create_peer_request(OPT_GET_CHUNK, i) for i in range(num_chunks)]
        
        curr_chunk = 0
        while curr_chunk < num_chunks:
            curr_peer = curr_chunk % num_peers
            await self.client.connect_to_peer(
                peer_list[curr_peer][IP],
                peer_list[curr_peer][PORT],
                request_list[curr_chunk]
            )
            curr_chunk += 1

    async def download_file(self, num_chunks: int, filename: str):
        """
        Download file chunks and save to output directory
        """
        await self.distribute_chunks_evenly(num_chunks)

        while not self.client.chunk_buffer.has_all_chunks:
            continue
        
        chunks = []
        output_path = f'output/{self.client.id}_{filename}'
        for i in range(self.client.chunk_buffer.get_size()):
            chunks.append(self.client.chunk_buffer.get_data(i))

        try:
            fh.decode_file(chunks, output_path)
            print(f"[info] file downloaded successfully: {output_path}")
        except:
            print(f"[error] failed to save downloaded file: {filename}")

    def upload_file(self, filename: str) -> int:
        """
        Prepare file for seeding by splitting into chunks
        """
        try:
            chunks_size, chunks = fh.encode_file(filename)
            self.client.chunk_buffer.set_buffer(chunks_size)
            for idx, chunk_data in enumerate(chunks):
                self.client.chunk_buffer.add_data(Chunk(idx, chunk_data))
            return chunks_size
        except:
            print(f"[error] failed to read file: '{filename}'")
            return 0

    def strip_filename(self, filename: str) -> str:
        """
        Strip directory path and escape chars from filename
        """
        size = len(filename)
        stripped = ""
        for idx in range(size-1, -1, -1):
            if filename[idx] in ['/', '\'']:
                break
            stripped += filename[idx]
        return stripped[::-1]

    def display_torrent_list(self, torrent_list):
        """
        Display formatted list of available torrents
        """
        print("\n" + "="*100 + "\n")
        print("TID\tFILE_NAME\tTOTAL_CHUNKS\tSEEDERS")
        print("-"*100)
        for torrent in torrent_list:
            print(f"{torrent[TID]}\t{torrent[FILE_NAME]}\t{torrent[TOTAL_CHUNKS]}\t\t{torrent[SEEDER_LIST]}\n")
        print("\n" + "="*100 + "\n")

class Client:
    """
    Client is either seeder or leecher.
    """
    def __init__(self, ip, port):
        self.id = self.generate_id(ip, port)
        self.ip = ip
        self.port = port
        self.state = State()
        self.helper = ClientHelper(self)
        self.seeder_list = {}
        self.chunk_buffer = None
        self.torrent_id = None
    
    @staticmethod
    def generate_id(ip: str, port: str) -> str:
        return hashlib.md5((ip + port).encode()).hexdigest()
    
    async def register_to_tracker(self, ip, port):
        """
        Connect to tracker server
        """
        if ip is None:
            ip = "127.0.0.1"
        if port is None:
            port = "8080"
            
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            return reader, writer
        except ConnectionError:
            print("[error] failed to connect to tracker")
            sys.exit(-1)

    async def connect_to_peer(self, ip, port, requests):
        """
        Connect to peer, send request payload and handle response
        """
        try:
            print(f"[info] connecting to seeder at {ip}:{port}")
            reader, writer = await asyncio.open_connection(ip, int(port))
            print(f"[info] connected as leecher: {self.ip}:{self.port}")
        except ConnectionError:
            print("[error] failed to connect to peer")
            sys.exit(-1)

        await self.send_message(writer, requests)
        res = await self.receive_message(reader)
        writer.close()
        return res

    async def receive_peer_request(self, reader, writer):
        """
        Handle incoming peer requests and send response
        """
        try:
            data = await reader.read(READ_SIZE)
            peer_request = json.loads(data.decode())
            addr = writer.get_extra_info('peername')

            print(f"[debug] received from {addr}: {peer_request}")
            response = self.handle_peer_request(peer_request)
            payload = json.dumps(response)
            print(f"[debug] sending response: {payload}")
            writer.write(payload.encode())
            await writer.drain()
            print(f"[debug] closing connection to {addr}")
        except:
            print(f"[info] peer {writer.get_extra_info('peername')} disconnected")
        finally:
            writer.close()

    async def start_seeding(self):
        """
        Start seeding server to handle peer requests
        """
        server = await asyncio.start_server(self.receive_peer_request, self.ip, self.port)
        if server is None:
            return
        addr = server.sockets[0].getsockname()
        print(f'[info] seeding started on {addr}')
        async with server:
            try:
                await server.serve_forever()
            except:
                pass
            finally:
                server.close()
                await server.wait_closed()

    async def receive_message(self, reader):
        """
        Receive and decode messages, route to appropriate handler
        """
        data = await reader.read(READ_SIZE)
        payload = json.loads(data.decode())
        print(f'[debug] received message: {payload}')
        opc = payload[OPC]
        if opc > 9:
            res = await self.handle_server_response(payload)
        else:
            res = self.handle_peer_response(payload)
        return res

    async def send_message(self, writer, payload: dict):
        """
        Encode and send message payload
        """
        json_payload = json.dumps(payload)
        print(f"[debug] sending message: {json_payload}")
        writer.write(json_payload.encode())
        await writer.drain()

    async def handle_server_response(self, response) -> int:
        """
        Handle server response and return appropriate status code
        """
        ret = response[RET]
        opc = response[OPC]

        # Handle error responses
        if ret == RET_FAIL:
            print("[error] server request failed")
            return -1
        elif ret == RET_ALREADY_SEEDING:
            print("[error] already seeding a file")
            return -1
        elif ret == RET_NO_AVAILABLE_TORRENTS:
            print("[error] no torrents available")
            return -1
        elif ret == RET_TORRENT_DOES_NOT_EXIST:
            print("[error] torrent id does not exist")
            return -1

        # Handle successful responses
        if opc == OPT_GET_LIST:
            self.helper.display_torrent_list(response[TORRENT_LIST])
            return RET_SUCCESS
            
        elif opc == OPT_GET_TORRENT:
            torrent = response[TORRENT]
            self.state.leeching = True
            self.seeder_list = torrent[SEEDER_LIST]
            self.chunk_buffer.set_buffer(torrent[TOTAL_CHUNKS])
            await self.helper.download_file(torrent[TOTAL_CHUNKS], torrent[FILE_NAME])
            return RET_FINISHED_DOWNLOAD    
            
        elif opc == OPT_START_SEED or opc == OPT_UPLOAD_FILE:
            self.state.leeching = False
            self.state.seeding = True
            self.torrent_id = response[TID]
            await self.start_seeding()
            return RET_FINSH_SEEDING
            
        elif opc == OPT_STOP_SEED:
            self.state.seeding = False
            return RET_FINSH_SEEDING

        return 1

    def create_server_request(self, opc: int, torrent_id=None, filename=None) -> dict:
        """
        Create server request payload
        """
        payload = {
            OPC: opc,
            IP: self.ip,
            PORT: self.port,
            PID: self.id
        }

        if opc in [OPT_GET_TORRENT, OPT_START_SEED, OPT_STOP_SEED]:
            payload[TID] = torrent_id
        elif opc == OPT_UPLOAD_FILE:
            num_chunks = self.helper.upload_file(filename)
            if num_chunks == 0:
                return {}
            payload[FILE_NAME] = self.helper.strip_filename(filename)
            payload[TOTAL_CHUNKS] = num_chunks

        return payload

    def handle_peer_response(self, response) -> int:
        """
        Handle peer response
        """
        ret = response[RET]
        opc = response[OPC]

        if ret == RET_FAIL or ret != RET_SUCCESS:
            return -1
        
        if opc == OPT_GET_PEERS:
            self.seeder_list = response[PEER_LIST]
        elif opc == OPT_GET_CHUNK:
            data = response[CHUNK_DATA]
            idx = response[CHUNK_IDX]
            new_chunk = Chunk(idx, data)
            self.chunk_buffer.add_data(new_chunk)
        
        return RET_SUCCESS

    def handle_peer_request(self, request) -> dict:
        """
        Handle peer request and return response
        """
        opc = request[OPC]
        response = {
            OPC: opc,
            IP: self.ip,
            PORT: self.port
        }

        if opc == OPT_GET_PEERS:
            response[PEER_LIST] = self.seeder_list
            response[RET] = RET_SUCCESS
        elif opc == OPT_GET_CHUNK:
            chunk_idx = request[CHUNK_IDX]
            if self.chunk_buffer.has_chunk(chunk_idx):
                response[CHUNK_DATA] = self.chunk_buffer.get_data(chunk_idx)
                response[CHUNK_IDX] = request[CHUNK_IDX]
                response[RET] = RET_SUCCESS
            else:
                response[RET] = RET_FAIL
        return response
        
    def create_peer_request(self, opc: int, chunk_idx=None) -> dict:
        """
        Create peer request payload
        """
        payload = {
            OPC: opc,
            IP: self.ip,
            PORT: self.port
        }
        if opc == OPT_GET_CHUNK:
            payload[CHUNK_IDX] = chunk_idx
        return payload