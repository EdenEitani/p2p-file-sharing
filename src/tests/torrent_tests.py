"""
Tests for Torrent class
"""
import unittest
from torrent import Torrent
from protocol import PayloadField

class TestTorrent(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.torrent = Torrent(1, "test.txt", 10)
        self.peer_id = "test_peer"
        self.ip = "127.0.0.1"
        self.port = "8000"

    def test_torrent_initialization(self):
        """Test torrent object initialization"""
        self.assertEqual(self.torrent.id, 1)
        self.assertEqual(self.torrent.filename, "test.txt")
        self.assertEqual(self.torrent.num_of_chunks, 10)
        self.assertEqual(len(self.torrent.seeders), 0)
        self.assertEqual(len(self.torrent.leechers), 0)

    def test_add_seeder(self):
        """Test adding a seeder"""
        self.torrent.add_seeder(self.peer_id, self.ip, self.port)
        self.assertIn(self.peer_id, self.torrent.seeders)
        seeder = self.torrent.seeders[self.peer_id]
        self.assertEqual(seeder[PayloadField.IP_ADDRESS], self.ip)
        self.assertEqual(seeder[PayloadField.PORT], self.port)

    def test_add_leecher(self):
        """Test adding a leecher"""
        self.torrent.add_leecher(self.peer_id, self.ip, self.port)
        self.assertIn(self.peer_id, self.torrent.leechers)
        leecher = self.torrent.leechers[self.peer_id]
        self.assertEqual(leecher[PayloadField.IP_ADDRESS], self.ip)
        self.assertEqual(leecher[PayloadField.PORT], self.port)

    def test_remove_seeder(self):
        """Test removing a seeder"""
        self.torrent.add_seeder(self.peer_id, self.ip, self.port)
        self.torrent.remove_seeder(self.peer_id)
        self.assertNotIn(self.peer_id, self.torrent.seeders)

    def test_get_seeders(self):
        """Test getting seeder list"""
        self.torrent.add_seeder(self.peer_id, self.ip, self.port)
        seeders = self.torrent.get_seeders()
        self.assertEqual(len(seeders), 1)
        self.assertIn(self.peer_id, seeders)