#!/usr/bin/env python3
"""
Simple multicast listener to see what packets are being sent
"""

import socket
import struct
import sys

def listen_multicast(mcast_group, port=5006, timeout=10):
    """Listen for multicast packets"""
    
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Set SO_REUSEPORT if available
    if hasattr(socket, 'SO_REUSEPORT'):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    
    # Bind to any port
    sock.bind(('', 0))
    bound_port = sock.getsockname()[1]
    print(f"Bound to port {bound_port}")
    
    # Join multicast group
    mreq = struct.pack('=4s4s',
                      socket.inet_aton(mcast_group),
                      socket.inet_aton('0.0.0.0'))  # Any interface
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    print(f"Joined multicast group {mcast_group}")
    
    sock.settimeout(timeout)
    
    print(f"Listening for {timeout} seconds...")
    print()
    
    packet_count = 0
    try:
        while True:
            try:
                data, addr = sock.recvfrom(8192)
                packet_count += 1
                print(f"Packet #{packet_count} from {addr}: {len(data)} bytes")
                print(f"  Type byte: {data[0]} ({'STATUS' if data[0] == 0 else 'CMD' if data[0] == 1 else 'UNKNOWN'})")
                print(f"  First 32 bytes: {' '.join(f'{b:02x}' for b in data[:32])}")
                print()
                
                if packet_count >= 10:
                    print("Received 10 packets, stopping...")
                    break
                    
            except socket.timeout:
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    sock.close()
    print(f"\nTotal packets received: {packet_count}")


if __name__ == '__main__':
    # Resolve bee1-hf-status.local
    import subprocess
    
    hostname = "bee1-hf-status.local"
    
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_DGRAM)
        mcast_addr = addr_info[0][4][0]
        print(f"Resolved {hostname} to {mcast_addr}")
        print()
        
        listen_multicast(mcast_addr, timeout=10)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
