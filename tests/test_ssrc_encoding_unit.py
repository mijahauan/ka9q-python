import unittest
from ka9q.control import allocate_ssrc
from ka9q.types import Encoding

class TestEncodingSSRC(unittest.TestCase):
    def test_ssrc_uniqueness_with_encoding(self):
        """Verify that providing encoding changes the SSRC"""
        params = {
            'frequency_hz': 14074000.0,
            'preset': 'iq',
            'sample_rate': 16000,
            'agc': False,
            'gain': 0.0,
            'destination': None
        }
        
        # 1. Base SSRC (no encoding or 0)
        ssrc_base = allocate_ssrc(**params)
        
        # 2. SSRC with F32
        ssrc_f32 = allocate_ssrc(**params, encoding=Encoding.F32)
        
        # 3. SSRC with S16LE
        ssrc_s16 = allocate_ssrc(**params, encoding=Encoding.S16LE)
        
        # Verify all are different
        self.assertNotEqual(ssrc_base, ssrc_f32, "SSRC with encoding should differ from base")
        self.assertNotEqual(ssrc_f32, ssrc_s16, "SSRCs for different encodings should differ")
        
        # Verify determinism
        ssrc_f32_2 = allocate_ssrc(**params, encoding=Encoding.F32)
        self.assertEqual(ssrc_f32, ssrc_f32_2, "SSRC should be deterministic for same encoding")

if __name__ == '__main__':
    unittest.main()
