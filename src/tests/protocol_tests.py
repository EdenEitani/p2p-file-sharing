"""
Tests for protocol enums and constants
"""
import unittest
from protocol import PeerServerOperation, PeerOperation, ReturnCode, PayloadField

class TestProtocol(unittest.TestCase):
    def test_peer_server_operations(self):
        """Test peer to server operation codes"""
        self.assertEqual(PeerServerOperation.GET_LIST, 10)
        self.assertEqual(PeerServerOperation.GET_TORRENT, 11)
        self.assertEqual(PeerServerOperation.START_SEED, 12)
        self.assertEqual(PeerServerOperation.STOP_SEED, 13)
        self.assertEqual(PeerServerOperation.UPLOAD_FILE, 14)

    def test_peer_operations(self):
        """Test peer to peer operation codes"""
        self.assertEqual(PeerOperation.STATUS_INTERESTED, 1)
        self.assertEqual(PeerOperation.GET_PEERS, 5)
        self.assertEqual(PeerOperation.GET_CHUNK, 6)

    def test_return_codes(self):
        """Test return codes"""
        self.assertEqual(ReturnCode.SUCCESS, 0)
        self.assertEqual(ReturnCode.FAIL, -1)
        self.assertEqual(ReturnCode.ALREADY_SEEDING, -2)

    def test_payload_fields(self):
        """Test payload field names"""
        self.assertEqual(PayloadField.OPERATION_CODE, 'OP_CODE')
        self.assertEqual(PayloadField.IP_ADDRESS, 'IP_ADDRESS')
        self.assertEqual(PayloadField.TORRENT_ID, 'TORRENT_ID')