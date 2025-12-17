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
        
    def test_empty_input(self):
        """Verify error on empty input"""
        with self.assertRaises(ValueError):
            generate_multicast_ip("")

if __name__ == '__main__':
    unittest.main()
