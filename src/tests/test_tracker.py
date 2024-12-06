"""
Tests for TrackerServer class
"""
import unittest
from tracker import TrackerServer
from protocol import PeerServerOperation, ReturnCode, PayloadField

class TestTrackerServer(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = TrackerServer()
        self.peer_id = "test_peer"
        self.ip = "127.0.0.1"
        self.port = "8000"

    def test_add_new_file(self):
        """Test adding a new file to tracker"""
        request = {
            PayloadField.PEER_ID: self.peer_id,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port,
            PayloadField.FILE_NAME: "test.txt",
            PayloadField.NUM_OF_CHUNKS: 10
        }
        status, torrent_id = self.tracker.add_new_file(request)
        self.assertEqual(status, ReturnCode.SUCCESS)
        self.assertEqual(torrent_id, 0)
        self.assertEqual(len(self.tracker.torrents), 1)

    def test_get_torrent_list_empty(self):
        """Test getting torrent list when empty"""
        response = self.tracker._handle_get_list()
        self.assertEqual(response[PayloadField.RETURN_CODE], ReturnCode.NO_AVAILABLE_TORRENTS)

    def test_get_torrent_list_with_torrents(self):
        """Test getting torrent list with torrents"""
        request = {
            PayloadField.PEER_ID: self.peer_id,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port,
            PayloadField.FILE_NAME: "test.txt",
            PayloadField.NUM_OF_CHUNKS: 10
        }
        self.tracker.add_new_file(request)
        
        response = self.tracker._handle_get_list()
        self.assertEqual(response[PayloadField.RETURN_CODE], ReturnCode.SUCCESS)
        self.assertEqual(len(response[PayloadField.TORRENT_LIST]), 1)

    def test_handle_get_torrent_not_exists(self):
        """Test getting non-existent torrent"""
        request = {
            PayloadField.TORRENT_ID: 999,
            PayloadField.PEER_ID: self.peer_id,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port
        }
        response = self.tracker._handle_get_torrent(request)
        self.assertEqual(response[PayloadField.RETURN_CODE], ReturnCode.TORRENT_DOES_NOT_EXIST)

    def test_handle_stop_seed(self):
        """Test stopping seeding"""
        add_request = {
            PayloadField.PEER_ID: self.peer_id,
            PayloadField.IP_ADDRESS: self.ip,
            PayloadField.PORT: self.port,
            PayloadField.FILE_NAME: "test.txt",
            PayloadField.NUM_OF_CHUNKS: 10
        }
        status, torrent_id = self.tracker.add_new_file(add_request)
        
        stop_request = {
            PayloadField.TORRENT_ID: torrent_id,
            PayloadField.PEER_ID: self.peer_id
        }
        response = self.tracker._handle_stop_seed(stop_request)
        self.assertEqual(response[PayloadField.RETURN_CODE], ReturnCode.SUCCESS)