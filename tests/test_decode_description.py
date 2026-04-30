import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q.control import RadiodControl
from ka9q.types import StatusType

class TestDescriptionDecoding(unittest.TestCase):
    """Test SDR description decoding"""
    
    @patch('ka9q.control.RadiodControl._connect', return_value=None)
    def test_decode_description(self, mock_connect):
        """Verify that _decode_status_response decodes StatusType.DESCRIPTION correctly"""
        # Create a RadiodControl instance (now safe due to mock)
        control = RadiodControl("radiod.local")
        
        # Manually set attributes that __init__ might not have set due to mocked _connect
        control.status_mcast_addr = "239.1.1.1"
        control.metrics = MagicMock()
        # Create a dummy status packet with a description
        # Format: Packet Type (0), Tag (4), Length (N), Data (SDR Name)
        description = "AirspyHF+"
        desc_bytes = description.encode('utf-8')
        desc_len = len(desc_bytes)
        
        # Construct buffer
        # 0x00: Status packet type
        # 0x04: StatusType.DESCRIPTION
        # desc_len: Length
        # desc_bytes: SDR Name
        # 0xff: StatusType.EOL
        buffer = bytes([0, StatusType.DESCRIPTION, desc_len]) + desc_bytes + bytes([StatusType.EOL])
        
        # Decode
        status = control._decode_status_response(buffer)
        
        # Verify
        self.assertIn('description', status)
        self.assertEqual(status['description'], description)

if __name__ == "__main__":
    unittest.main()
