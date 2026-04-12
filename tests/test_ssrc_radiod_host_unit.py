import unittest
from ka9q.control import allocate_ssrc


class TestRadiodHostSSRC(unittest.TestCase):
    def test_ssrc_uniqueness_with_radiod_host(self):
        """Same channel params on different radiod instances produce different SSRCs"""
        params = {
            'frequency_hz': 14074000.0,
            'preset': 'iq',
            'sample_rate': 16000,
            'agc': False,
            'gain': 0.0,
        }

        ssrc_base = allocate_ssrc(**params)
        ssrc_a = allocate_ssrc(**params, radiod_host="sdr1-hf-status.local")
        ssrc_b = allocate_ssrc(**params, radiod_host="sdr2-hf-status.local")

        self.assertNotEqual(ssrc_base, ssrc_a,
                            "SSRC with radiod_host should differ from base")
        self.assertNotEqual(ssrc_base, ssrc_b,
                            "SSRC with radiod_host should differ from base")
        self.assertNotEqual(ssrc_a, ssrc_b,
                            "SSRCs for different radiod hosts should differ")

    def test_ssrc_determinism_with_radiod_host(self):
        """Same (params, radiod_host) pair always produces the same SSRC"""
        params = {
            'frequency_hz': 14074000.0,
            'preset': 'iq',
            'sample_rate': 16000,
            'agc': False,
            'gain': 0.0,
            'radiod_host': "sdr1-hf-status.local",
        }

        ssrc1 = allocate_ssrc(**params)
        ssrc2 = allocate_ssrc(**params)
        self.assertEqual(ssrc1, ssrc2,
                         "Same params + radiod_host should produce same SSRC")

    def test_radiod_host_combined_with_destination(self):
        """radiod_host and destination both contribute to SSRC uniqueness"""
        params = {
            'frequency_hz': 14074000.0,
            'preset': 'iq',
            'sample_rate': 16000,
            'agc': False,
            'gain': 0.0,
            'destination': "239.1.1.1",
        }

        ssrc_a = allocate_ssrc(**params, radiod_host="sdr1.local")
        ssrc_b = allocate_ssrc(**params, radiod_host="sdr2.local")
        self.assertNotEqual(ssrc_a, ssrc_b,
                            "Same destination + different radiod should differ")


if __name__ == '__main__':
    unittest.main()
