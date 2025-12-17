import unittest
from ka9q.control import allocate_ssrc

class TestDestinationSSRC(unittest.TestCase):
    def test_ssrc_uniqueness_with_destination(self):
        """Verify that providing a destination changes the SSRC"""
        params = {
            'frequency_hz': 14074000.0,
            'preset': 'iq',
            'sample_rate': 16000,
            'agc': False,
            'gain': 0.0
        }
        
        # 1. Base SSRC (no destination)
        ssrc_base = allocate_ssrc(**params)
        
        # 2. SSRC with destination A
        ssrc_a = allocate_ssrc(**params, destination="239.1.1.1")
        
        # 3. SSRC with destination B
        ssrc_b = allocate_ssrc(**params, destination="239.2.2.2")
        
        # Verify all are different
        self.assertNotEqual(ssrc_base, ssrc_a, "SSRC with dest should differ from base")
        self.assertNotEqual(ssrc_base, ssrc_b, "SSRC with dest should differ from base")
        self.assertNotEqual(ssrc_a, ssrc_b, "SSRCs for different destinations should differ")
        
        # Verify determinism
        ssrc_a_2 = allocate_ssrc(**params, destination="239.1.1.1")
        self.assertEqual(ssrc_a, ssrc_a_2, "SSRC should be deterministic for same destination")

if __name__ == '__main__':
    unittest.main()
