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
        
    async def split_chunks_between_peers(self, num_chunks: int, max_retries=3, retry_delay=1):
        """Split torrent chunks beetween available peers"""
        logger.info(f"Starting distribution of {num_chunks} chunks")
        num_peers = len(self.client.seeder_list)
        peer_list = list(self.client.seeder_list.values())
        failed_chunks = set(range(num_chunks))
        retry_count = 0

        while failed_chunks and retry_count < max_retries:
            if retry_count > 0:
                logger.info(f"Retry attempt {retry_count} for chunks: {failed_chunks}")
                await asyncio.sleep(retry_delay)

            # Try to download each missing chunk
            for chunk_idx in list(failed_chunks): 
                curr_peer = chunk_idx % num_peers
                request = self.client.create_peer_request(PeerOperation.GET_CHUNK, chunk_idx)
                
                try:
                    result = await self.client.connect_to_peer(
                        peer_list[curr_peer][PayloadField.IP_ADDRESS],
                        peer_list[curr_peer][PayloadField.PORT],
                        request
                    )
                    
                    if result == ReturnCode.SUCCESS and self.client.chunk_buffer.has_chunk(chunk_idx):
                        failed_chunks.remove(chunk_idx)
                        logger.info(f"Successfully downloaded chunk {chunk_idx} from peer {curr_peer}")
                    else:
                        logger.error(f"Failed to download chunk {chunk_idx} from peer {curr_peer}")
                except Exception as e:
                    logger.error(f"Error downloading chunk {chunk_idx}: {str(e)}")

            retry_count += 1

        if failed_chunks:
            missing = len(failed_chunks)
            total = num_chunks
            logger.error(f"Failed to download {missing}/{total} chunks after {max_retries} retries")
            logger.error(f"Missing chunks: {failed_chunks}")
            return False
        
        logger.info("All chunks downloaded successfully")
        return True

    async def download_file(self, num_chunks: int, filename: str):
        if not await self.split_chunks_between_peers(num_chunks):
            logger.error("Failed to download all chunks")
            return False

        chunks = []
        output_path = f'output/{self.client.id}_{filename}'
        for i in range(self.client.chunk_buffer.get_size()):
            chunks.append(self.client.chunk_buffer.get_data(i))

        try:
            fh.decode_file(chunks, output_path)
            logger.info(f"File downloaded successfully: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save downloaded file {filename}: {str(e)}")
            return False

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
        size = len(filename)
        stripped = ""
        for idx in range(size-1, -1, -1):
            if filename[idx] in ['/', '\'']:
                break
            stripped += filename[idx]
        return stripped[::-1]

    def display_torrent_list(self, torrent_list):
        id_width = 6
        name_width = 20
        chunks_width = 15
        label_width = 10

        print("\n" + "=" * 120)
        headers = [
            "ID".ljust(id_width),
            "File Name".ljust(name_width),
            "Chunks".ljust(chunks_width),
            "Peers"
        ]
        print("  ".join(headers))
        print("-" * 120)

        for torrent in torrent_list:
            base_info = [
                str(torrent[PayloadField.TORRENT_ID]).ljust(id_width),
                torrent[PayloadField.FILE_NAME][:name_width-3].ljust(name_width),
                str(torrent[PayloadField.NUM_OF_CHUNKS]).ljust(chunks_width),
                "" 
            ]
            print("  ".join(base_info))

            # Print seeders
            seeders = [f"{client_id}@{info['IP_ADDRESS']}:{info['PORT']}" 
                    for client_id, info in torrent[PayloadField.SEEDER_LIST].items()]
            if seeders:
                print(f"{' ' * (id_width + name_width + chunks_width + 4)}{'Seeders:'.ljust(label_width)}", end="")
                for seeder in seeders:
                    print(seeder)
                    if seeder != seeders[-1]: 
                        print(f"{' ' * (id_width + name_width + chunks_width + label_width + 4)}", end="")

            # Print leechers
            leechers = [f"{client_id}@{info['IP_ADDRESS']}:{info['PORT']}" 
                    for client_id, info in torrent[PayloadField.LEECHER_LIST].items()]
            if leechers:
                print(f"{' ' * (id_width + name_width + chunks_width + 4)}{'Leechers:'.ljust(label_width)}", end="")
                for leecher in leechers:
                    print(leecher)
                    if leecher != leechers[-1]:
                        print(f"{' ' * (id_width + name_width + chunks_width + label_width + 4)}", end="")
            
            if not seeders and not leechers:
                print(f"{' ' * (id_width + name_width + chunks_width + 4)}No peers conßnected")
            
            print("-" * 120)

        print("=" * 120 + "\n")

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
    
    def get_state(self):
        return self.state
    
    def is_seeding(self):
        return self.state.seeding == True
    
    async def register_to_tracker(self, ip, port):
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
    
    def _filter_payload(self, payload):
        """
        Don't print whole chunk_data to better understand the logs.
        """
        if (type(payload) == str):
            return payload
        filtered_payload = payload
        if PayloadField.CHUNK_DATA in filtered_payload:
            chunk_data = filtered_payload[PayloadField.CHUNK_DATA]
            filtered_payload[PayloadField.CHUNK_DATA] = f"{chunk_data[:20]}..." if chunk_data else "None"
        return filtered_payload


    async def receive_peer_request(self, reader, writer):
        """Handle incoming peer requests and send response"""
        try:
            data = await reader.read(READ_SIZE)
            peer_request = json.loads(data.decode())
            addr = writer.get_extra_info('peername')

            logger.debug(f"received from {addr}: {peer_request}")
            response = self.handle_peer_request(peer_request)
            payload = json.dumps(response)
            logger.debug(f"sending response: {self._filter_payload(payload)}")
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
        try:
            logger.debug("Reading message")
            data = await reader.read(READ_SIZE)
            
            # Handle empty data
            if not data:
                logger.error("Received empty data")
                return ReturnCode.FAIL
                
            try:
                payload = json.loads(data.decode())
                logger.debug(f'Received message: {self._filter_payload(payload)}')
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                logger.error(f"Raw data received: {data.decode()}")
                
                # Retry logic for invalid responses
                for _ in range(3): 
                    logger.info("Retrying read...")
                    await asyncio.sleep(0.5)
                    data = await reader.read(READ_SIZE)
                    if data:
                        try:
                            payload = json.loads(data.decode())
                            logger.debug(f'Received message on retry: {payload}')
                            break
                        except json.JSONDecodeError:
                            continue
                else:
                    return ReturnCode.FAIL
                
            opcode = payload[PayloadField.OPERATION_CODE]
            if opcode > 9:
                res = await self.handle_server_response(payload)
            else:
                res = self.handle_peer_response(payload)
            return res
        except Exception as e:
            logger.error(f"Error in receive_message: {str(e)}")
            return ReturnCode.FAIL

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
        payload = {
            PayloadField.OPERATION_CODE: opcode,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port
        }
        if opcode == PeerOperation.GET_CHUNK:
            payload[PayloadField.CHUNK_IDX] = chunk_idx
        return payload