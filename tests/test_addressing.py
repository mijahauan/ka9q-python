import unittest
from ka9q import generate_multicast_ip

class TestAddressing(unittest.TestCase):
    def test_generate_multicast_ip_format(self):
        """Verify output format"""
        ip = generate_multicast_ip("test-app")
        self.assertTrue(ip.startswith("239."), f"IP {ip} should start with 239.")
        parts = ip.split(".")
        self.assertEqual(len(parts), 4, "IP should have 4 octets")
        for part in parts:
            val = int(part)
            self.assertTrue(0 <= val <= 255, f"Octet {val} out of range")
            
    def test_determinism(self):
        """Verify consistent output for same input"""
        ip1 = generate_multicast_ip("my-app-v1")
        ip2 = generate_multicast_ip("my-app-v1")
        self.assertEqual(ip1, ip2, "Same ID should produce same IP")
        
    def test_uniqueness(self):
        """Verify different inputs produce different IPs (high probability)"""
        ip1 = generate_multicast_ip("app-A")
        ip2 = generate_multicast_ip("app-B")
        self.assertNotEqual(ip1, ip2, "Different IDs should produce different IPs")
        
    def test_radiod_host_changes_result(self):
        """Same client ID with different radiod hosts produces different IPs"""
        ip1 = generate_multicast_ip("hf-timestd", radiod_host="sdr1.local")
        ip2 = generate_multicast_ip("hf-timestd", radiod_host="sdr2.local")
        self.assertNotEqual(ip1, ip2, "Different radiod hosts should produce different IPs")

    def test_radiod_host_determinism(self):
        """Same (client, radiod) pair always produces the same IP"""
        ip1 = generate_multicast_ip("hf-timestd", radiod_host="sdr1.local")
        ip2 = generate_multicast_ip("hf-timestd", radiod_host="sdr1.local")
        self.assertEqual(ip1, ip2, "Same (client, radiod) pair should produce same IP")

    def test_radiod_host_none_matches_legacy(self):
        """Omitting radiod_host produces the same result as the old API"""
        ip_legacy = generate_multicast_ip("my-app-v1")
        ip_none = generate_multicast_ip("my-app-v1", radiod_host=None)
        self.assertEqual(ip_legacy, ip_none, "None radiod_host should match legacy behaviour")

    def test_empty_input(self):
        """Verify error on empty input"""
        with self.assertRaises(ValueError):
            generate_multicast_ip("")

if __name__ == '__main__':
    unittest.main()
