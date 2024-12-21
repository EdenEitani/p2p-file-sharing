import unittest
import asyncio
import random
import time
from unittest.mock import Mock, patch
from client import Client
from protocol import PeerOperation, ReturnCode, PayloadField
from file_chunk import Chunk, ChunkBuffer

def async_test(f):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

class TestP2PPerformance(unittest.TestCase):
   def setUp(self):
       self.client = Client("127.0.0.1", "8000")
       self.test_data = b"x" * 16384
       self.default_seeder = {
           "peer1": {
               PayloadField.IP_ADDRESS: "127.0.0.1", 
               PayloadField.PORT: "8001"
           }
       }
       self.client.seeder_list = self.default_seeder

   async def mock_successful_download(self, *args, **kwargs):
       request = args[2]
       chunk_idx = request.get(PayloadField.CHUNK_IDX)
       self.client.chunk_buffer.add_data(Chunk(chunk_idx, self.test_data))
       return ReturnCode.SUCCESS

   @async_test
   async def test_download_speed_single_peer(self):
       chunk_count = 100
       self.client.chunk_buffer.set_buffer(chunk_count)
       
       with patch('client.Client.connect_to_peer') as mock_connect:
           mock_connect.side_effect = self.mock_successful_download
           
           start_time = time.time()
           result = await self.client.helper.split_chunks_between_peers(chunk_count)
           end_time = time.time()

           self.assertTrue(result)
           self.assertEqual(self.client.chunk_buffer.get_size(), chunk_count)
           
           total_size = chunk_count * len(self.test_data)
           speed = total_size / (end_time - start_time) / 1024 / 1024
           print(f"\nSingle peer download speed: {speed:.2f} MB/s")

   @async_test
   async def test_multi_peer_efficiency(self):
       chunk_count = 200
       peer_counts = [1, 2, 4, 8]
       results = {}

       for peer_count in peer_counts:
           self.client.chunk_buffer = ChunkBuffer()
           self.client.chunk_buffer.set_buffer(chunk_count)
           self.client.seeder_list = {
               f"peer{i}": {
                   PayloadField.IP_ADDRESS: f"127.0.0.{i}",
                   PayloadField.PORT: str(8000 + i)
               }
               for i in range(1, peer_count + 1)
           }

           with patch('client.Client.connect_to_peer') as mock_connect:
               mock_connect.side_effect = self.mock_successful_download
               
               start_time = time.time()
               result = await self.client.helper.split_chunks_between_peers(chunk_count)
               end_time = time.time()

               self.assertTrue(result)
               self.assertEqual(self.client.chunk_buffer.get_size(), chunk_count)

               total_size = chunk_count * len(self.test_data)
               speed = total_size / (end_time - start_time) / 1024 / 1024
               results[peer_count] = speed

       print("\nMulti-peer efficiency:")
       for peers, speed in results.items():
           print(f"{peers} peers: {speed:.2f} MB/s")
           if peers > 1:
               print(f"Efficiency gain: {speed/results[1]:.2f}x")

   @async_test
   async def test_network_congestion(self):
       chunk_count = 50
       self.client.chunk_buffer.set_buffer(chunk_count)

       async def delayed_download(*args, **kwargs):
           await asyncio.sleep(0.01)  # 10ms delay
           request = args[2]
           chunk_idx = request.get(PayloadField.CHUNK_IDX)
           self.client.chunk_buffer.add_data(Chunk(chunk_idx, self.test_data))
           return ReturnCode.SUCCESS

       with patch('client.Client.connect_to_peer') as mock_connect:
           mock_connect.side_effect = delayed_download
           
           start_time = time.time()
           result = await self.client.helper.split_chunks_between_peers(chunk_count)
           total_time = time.time() - start_time

           self.assertTrue(result)
           self.assertEqual(self.client.chunk_buffer.get_size(), chunk_count)
           print(f"\nDownload time with 10ms latency: {total_time:.2f}s")

   @async_test
   async def test_failure_recovery_time(self):
    chunk_count = 30
    max_retries = 10
    retry_delay = 0.2  # Add delay between retries
    
    for fail_rate in [0.1, 0.25, 0.5]:
        self.client.chunk_buffer = ChunkBuffer()
        self.client.chunk_buffer.set_buffer(chunk_count)
        failed_chunks = set()

        async def fail_sometimes(*args, **kwargs):
            request = args[2]
            chunk_idx = request.get(PayloadField.CHUNK_IDX)
            
            if chunk_idx in failed_chunks and len(failed_chunks) >= (chunk_count * fail_rate):
                failed_chunks.remove(chunk_idx)
                self.client.chunk_buffer.add_data(Chunk(chunk_idx, self.test_data))
                return ReturnCode.SUCCESS
                
            if random.random() < fail_rate:
                failed_chunks.add(chunk_idx)
                await asyncio.sleep(retry_delay)
                return ReturnCode.FAILED_TO_DOWNLOAD
                
            self.client.chunk_buffer.add_data(Chunk(chunk_idx, self.test_data))
            return ReturnCode.SUCCESS

        with patch('client.Client.connect_to_peer') as mock_connect:
            mock_connect.side_effect = fail_sometimes
            
            start_time = time.time()
            result = await self.client.helper.split_chunks_between_peers(
                chunk_count, 
                max_retries=max_retries,
                retry_delay=retry_delay
            )
            recovery_time = time.time() - start_time

            self.assertTrue(result)
            self.assertEqual(self.client.chunk_buffer.get_size(), chunk_count)
            print(f"\nRecovery time with {fail_rate*100}% failure rate: {recovery_time:.2f}s")

   @async_test
   async def test_concurrent_downloads(self):
       max_concurrent = 5
       chunk_per_download = 20
       
       with patch('client.Client.connect_to_peer') as mock_connect:
           mock_connect.side_effect = self.mock_successful_download
           
           tasks = []
           for _ in range(max_concurrent):
               self.client.chunk_buffer = ChunkBuffer()
               self.client.chunk_buffer.set_buffer(chunk_per_download)
               task = asyncio.create_task(
                   self.client.helper.split_chunks_between_peers(chunk_per_download)
               )
               tasks.append(task)

           start_time = time.time()
           results = await asyncio.gather(*tasks)
           total_time = time.time() - start_time

           self.assertTrue(all(results))
           print(f"\nConcurrent downloads ({max_concurrent}x{chunk_per_download} chunks)")
           print(f"Total time: {total_time:.2f}s")
           print(f"Average time per download: {total_time/max_concurrent:.2f}s")

if __name__ == '__main__':
   unittest.main()