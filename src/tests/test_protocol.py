"""Tests for protocol enums and constants"""
import unittest
from protocol import PeerServerOperation, PeerOperation, ReturnCode, PayloadField

class TestProtocol(unittest.TestCase):
    def test_peer_server_operations(self):
        """Test peer to server operation codes (100-149)"""
        self.assertEqual(PeerServerOperation.GET_LIST, 100)
        self.assertEqual(PeerServerOperation.GET_TORRENT, 110)
        self.assertEqual(PeerServerOperation.START_SEED, 120)
        self.assertEqual(PeerServerOperation.STOP_SEED, 130)
        self.assertEqual(PeerServerOperation.UPLOAD_FILE, 140)

    def test_peer_operations(self):
        """Test peer to peer operation codes (150-199)"""
        self.assertEqual(PeerOperation.STATUS_INTERESTED, 150)
        self.assertEqual(PeerOperation.STATUS_UNINTERESTED, 160)
        self.assertEqual(PeerOperation.STATUS_CHOKED, 170)
        self.assertEqual(PeerOperation.STATUS_UNCHOKED, 180)
        self.assertEqual(PeerOperation.GET_PEERS, 190)
        self.assertEqual(PeerOperation.GET_CHUNK, 195)

    def test_return_codes(self):
        """Test return codes"""
        # Success codes (200-299)
        self.assertEqual(ReturnCode.SUCCESS, 200)
        self.assertEqual(ReturnCode.FINISHED_DOWNLOAD, 201)
        self.assertEqual(ReturnCode.FINISHED_SEEDING, 202)
        
        # Error codes (400-499)
        self.assertEqual(ReturnCode.BAD_REQUEST, 400)
        self.assertEqual(ReturnCode.UNAUTHORIZED, 401)
        self.assertEqual(ReturnCode.FORBIDDEN, 403)
        self.assertEqual(ReturnCode.NOT_FOUND, 404)
        self.assertEqual(ReturnCode.ALREADY_SEEDING, 409)
        self.assertEqual(ReturnCode.NO_AVAILABLE_TORRENTS, 410)
        self.assertEqual(ReturnCode.TORRENT_DOES_NOT_EXIST, 411)
        self.assertEqual(ReturnCode.FAIL, 450)

    def test_payload_fields(self):
        """Test payload field names"""
        self.assertEqual(PayloadField.OPERATION_CODE, 'OP_CODE')
        self.assertEqual(PayloadField.RETURN_CODE, 'RET_CODE')
        self.assertEqual(PayloadField.IP_ADDRESS, 'IP_ADDRESS')
        self.assertEqual(PayloadField.PORT, 'PORT')
        self.assertEqual(PayloadField.TORRENT_ID, 'TORRENT_ID')
        self.assertEqual(PayloadField.FILE_NAME, 'FILE_NAME')