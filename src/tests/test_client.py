"""
Tests for Client class
"""
import unittest
import asyncio
from client import Client, ClientHelper
from protocol import PeerOperation, PeerServerOperation, ReturnCode, PayloadField

class TestClient(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client("127.0.0.1", "8000")
        
    def test_client_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.ip, "127.0.0.1")
        self.assertEqual(self.client.port, "8000")
        self.assertFalse(self.client.state.seeding)
        self.assertFalse(self.client.state.leeching)

    def test_create_peer_request(self):
        """Test creating peer request"""
        request = self.client.create_peer_request(PeerOperation.GET_CHUNK, 1)
        self.assertEqual(request[PayloadField.OPERATION_CODE], PeerOperation.GET_CHUNK)
        self.assertEqual(request[PayloadField.IP_ADDRESS], "127.0.0.1")
        self.assertEqual(request[PayloadField.PORT], "8000")
        self.assertEqual(request[PayloadField.CHUNK_IDX], 1)

    def test_create_server_request(self):
        """Test creating server request"""
        request = self.client.create_server_request(
            PeerServerOperation.GET_TORRENT, 
            torrent_id=1
        )
        self.assertEqual(request[PayloadField.OPERATION_CODE], PeerServerOperation.GET_TORRENT)
        self.assertEqual(request[PayloadField.TORRENT_ID], 1)

    def test_handle_peer_request_get_peers(self):
        """Test handling peer request for getting peers"""
        request = {
            PayloadField.OPERATION_CODE: PeerOperation.GET_PEERS,
            PayloadField.IP_ADDRESS: "127.0.0.1",
            PayloadField.PORT: "8001"
        }
        response = self.client.handle_peer_request(request)
        self.assertEqual(response[PayloadField.RETURN_CODE], ReturnCode.SUCCESS)
        self.assertIn(PayloadField.PEER_LIST, response)

class TestClientHelper(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client("127.0.0.1", "8000")
        self.helper = ClientHelper(self.client)

    def test_strip_filename(self):
        """Test filename stripping"""
        filename = "/path/to/test.txt"
        stripped = self.helper.strip_filename(filename)
        self.assertEqual(stripped, "test.txt")