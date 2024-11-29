"""
Client functionality and actions for p2p file sharing.
"""
import hashlib
import asyncio
import sys
import json
from socket import *
import threading
from protocol import PeerOperation, PeerServerOperation, ReturnCode, PayloadField, READ_SIZE
from chunk import *
import file_handler as fh
from file_chunk import ChunkBuffer, Chunk
import os
from logger import setup_logger

logger = setup_logger()

def print_file_tree(start_path='.'):
    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{sub_indent}{f}")

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
        print("distribute_chunks_evenly")
        num_peers = len(self.client.seeder_list)
        peer_list = list(self.client.seeder_list.values())
        request_list = [self.client.create_peer_request(PeerOperation.GET_CHUNK, i) for i in range(num_chunks)]
        
        curr_chunk = 0
        while curr_chunk < num_chunks:
            curr_peer = curr_chunk % num_peers
            await self.client.connect_to_peer(
                peer_list[curr_peer][PayloadField.IP_ADDRESS],
                peer_list[curr_peer][PayloadField.PORT],
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
            logger.info(f"file downloaded successfully: {output_path}")
        except:
            logger.error(f"failed to save downloaded file: {filename}")

    def upload_file(self, filename: str) -> int:
        """
        Prepare file for seeding by splitting into chunks
        """
        try:
            logger.info(f"uploading file as seeder {filename}")
            chunks_size, chunks = fh.encode_file(filename)
            self.client.chunk_buffer.set_buffer(chunks_size)
            for idx, chunk_data in enumerate(chunks):
                self.client.chunk_buffer.add_data(Chunk(idx, chunk_data))
            return chunks_size
        except Exception as e:
            logger.error(f"{e} failed to read file: '{filename}'")
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
            print(f"{torrent[PayloadField.TORRENT_ID]}\t{torrent[PayloadField.FILE_NAME]}\t" + 
                  f"{torrent[PayloadField.NUM_OF_CHUNKS]}\t\t{torrent[PayloadField.SEEDER_LIST]}\n")
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
        self.chunk_buffer = ChunkBuffer()
    
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
            logger.error("failed to connect to tracker")
            sys.exit(-1)

    async def connect_to_peer(self, ip, port, requests):
        """
        Connect to peer, send request payload and handle response
        """
        try:
            logger.info(f"connecting to seeder at {ip}:{port}")
            reader, writer = await asyncio.open_connection(ip, int(port))
            logger.info(f"connected as leecher: {self.ip}:{self.port}")
        except ConnectionError:
            logger.error("failed to connect to peer")
            sys.exit(-1)

        await self.send_message(writer, requests)
        res = await self.receive_message(reader)
        writer.close()
        return res

    async def receive_peer_request(self, reader, writer):
        """Handle incoming peer requests and send response"""
        try:
            data = await reader.read(READ_SIZE)
            peer_request = json.loads(data.decode())
            addr = writer.get_extra_info('peername')

            logger.debug(f"received from {addr}: {peer_request}")
            response = self.handle_peer_request(peer_request)
            payload = json.dumps(response)
            logger.debug(f"sending response: {payload}")
            writer.write(payload.encode())
            await writer.drain()
            logger.debug(f"closing connection to {addr}")
        except:
            logger.info(f"peer {writer.get_extra_info('peername')} disconnected")
        finally:
            writer.close()

    async def start_seeding(self):
        """Start seeding server to handle peer requests"""
        addr = (self.ip, int(self.port))
        logger.info(f'Starting seeding server on {addr}')
        
        # Start server in a new thread
        thread = threading.Thread(target=self._run_seeding_thread, args=(addr,))
        thread.daemon = True  # Thread will exit when main program exits
        thread.start()
        
    def _run_seeding_thread(self, addr):
        """Run seeding server in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            server = loop.run_until_complete(
                asyncio.start_server(self.receive_peer_request, addr[0], addr[1], loop=loop)
            )
            logger.info(f'Seeding started on {server.sockets[0].getsockname()}')
            loop.run_forever()
        except Exception as e:
            logger.error(f"Seeding error: {str(e)}")
        finally:
            loop.close()

    async def receive_message(self, reader):
        """
        Receive and decode messages, route to appropriate handler
        """
        logger.debug("Reading message")
        data = await reader.read(READ_SIZE)
        payload = json.loads(data.decode())
        logger.debug(f'Received message: {payload}')
        opcode = payload[PayloadField.OPERATION_CODE]
        if opcode > 9:
            res = await self.handle_server_response(payload)
        else:
            res = self.handle_peer_response(payload)
        return res

    async def send_message(self, writer, payload: dict):
        """
        Encode and send message payload
        """
        json_payload = json.dumps(payload)
        logger.debug(f"sending message: {json_payload}")
        writer.write(json_payload.encode())
        await writer.drain()

    async def handle_server_response(self, response) -> int:
        """
        Handle server response and return appropriate status code
        """
        ret = response[PayloadField.RETURN_CODE]
        opcode = response[PayloadField.OPERATION_CODE]

        if ret == ReturnCode.FAIL:
            logger.error("server request failed")
            return -1
        elif ret == ReturnCode.ALREADY_SEEDING:
            logger.error("already seeding a file")
            return -1
        elif ret == ReturnCode.NO_AVAILABLE_TORRENTS:
            logger.error("no torrents available")
            return -1
        elif ret == ReturnCode.TORRENT_DOES_NOT_EXIST:
            logger.error("torrent id does not exist")
            return -1

        if opcode == PeerServerOperation.GET_LIST:
            self.helper.display_torrent_list(response[PayloadField.TORRENT_LIST])
            return ReturnCode.SUCCESS
            
        elif opcode == PeerServerOperation.GET_TORRENT:
            torrent = response[PayloadField.TORRENT_OBJECT]
            self.state.leeching = True
            self.seeder_list = torrent[PayloadField.SEEDER_LIST]
            self.chunk_buffer.set_buffer(torrent[PayloadField.NUM_OF_CHUNKS])
            await self.helper.download_file(torrent[PayloadField.NUM_OF_CHUNKS], torrent[PayloadField.FILE_NAME])
            return ReturnCode.FINISHED_DOWNLOAD    
            
        elif opcode == PeerServerOperation.START_SEED or opcode == PeerServerOperation.UPLOAD_FILE:
            self.state.leeching = False
            self.state.seeding = True
            self.torrent_id = response[PayloadField.TORRENT_ID]
            await self.start_seeding()
            return ReturnCode.SUCCESS
            
        elif opcode == PeerServerOperation.STOP_SEED:
            self.state.seeding = False
            return ReturnCode.FINISHED_SEEDING

        return 1

    def create_server_request(self, opcode: int, torrent_id=None, filename=None) -> dict:
        """
        Create server request payload
        """
        payload = {
            PayloadField.OPERATION_CODE: opcode,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port,
            PayloadField.PEER_ID: self.id
        }

        if opcode in [PeerServerOperation.GET_TORRENT, PeerServerOperation.START_SEED, PeerServerOperation.STOP_SEED]:
            payload[PayloadField.TORRENT_ID] = torrent_id
        elif opcode == PeerServerOperation.UPLOAD_FILE:
            num_chunks = self.helper.upload_file(filename)
            if num_chunks == 0:
                return {}
            payload[PayloadField.FILE_NAME] = self.helper.strip_filename(filename)
            payload[PayloadField.NUM_OF_CHUNKS] = num_chunks

        return payload

    def handle_peer_response(self, response) -> int:
        """
        Handle peer response
        """
        ret = response[PayloadField.RETURN_CODE]
        opcode = response[PayloadField.OPERATION_CODE]

        if ret == ReturnCode.FAIL or ret != ReturnCode.SUCCESS:
            return -1
        
        if opcode == PeerOperation.GET_PEERS:
            self.seeder_list = response[PayloadField.PEER_LIST]
        elif opcode == PeerOperation.GET_CHUNK:
            data = response[PayloadField.CHUNK_DATA]
            idx = response[PayloadField.CHUNK_IDX]
            new_chunk = Chunk(idx, data)
            self.chunk_buffer.add_data(new_chunk)
        
        return ReturnCode.SUCCESS

    def handle_peer_request(self, request) -> dict:
        """
        Handle peer request and return response
        """
        opcode = request[PayloadField.OPERATION_CODE]
        response = {
            PayloadField.OPERATION_CODE: opcode,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port
        }

        if opcode == PeerOperation.GET_PEERS:
            response[PayloadField.PEER_LIST] = self.seeder_list
            response[PayloadField.RETURN_CODE] = ReturnCode.SUCCESS
        elif opcode == PeerOperation.GET_CHUNK:
            chunk_idx = request[PayloadField.CHUNK_IDX]
            if self.chunk_buffer.has_chunk(chunk_idx):
                response[PayloadField.CHUNK_DATA] = self.chunk_buffer.get_data(chunk_idx)
                response[PayloadField.CHUNK_IDX] = request[PayloadField.CHUNK_IDX]
                response[PayloadField.RETURN_CODE] = ReturnCode.SUCCESS
            else:
                response[PayloadField.RETURN_CODE] = ReturnCode.FAIL
        return response
        
    def create_peer_request(self, opcode: int, chunk_idx=None) -> dict:
        """
        Create peer request payload
        """
        payload = {
            PayloadField.OPERATION_CODE: opcode,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port
        }
        if opcode == PeerOperation.GET_CHUNK:
            payload[PayloadField.CHUNK_IDX] = chunk_idx
        return payload