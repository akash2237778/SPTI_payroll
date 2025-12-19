#!/usr/bin/env python3
"""
ZK Device Connection Test Script
Tests different connection parameters to find what works
"""

from zk import ZK
import sys

DEVICE_IP = '192.168.2.66'
DEVICE_PORT = 4370

print(f"Testing connection to ZK device at {DEVICE_IP}:{DEVICE_PORT}")
print("=" * 60)

# Test configurations
configs = [
    {
        'name': 'Config 1: TCP, no ping',
        'params': {'timeout': 60, 'password': 0, 'force_udp': False, 'ommit_ping': True}
    },
    {
        'name': 'Config 2: UDP, no ping',
        'params': {'timeout': 60, 'password': 0, 'force_udp': True, 'ommit_ping': True}
    },
    {
        'name': 'Config 3: TCP, with ping',
        'params': {'timeout': 60, 'password': 0, 'force_udp': False, 'ommit_ping': False}
    },
    {
        'name': 'Config 4: UDP, with ping',
        'params': {'timeout': 60, 'password': 0, 'force_udp': True, 'ommit_ping': False}
    },
    {
        'name': 'Config 5: TCP, short timeout',
        'params': {'timeout': 10, 'password': 0, 'force_udp': False, 'ommit_ping': True}
    },
]

for config in configs:
    print(f"\n{config['name']}")
    print("-" * 60)
    
    try:
        zk = ZK(DEVICE_IP, port=DEVICE_PORT, **config['params'])
        print(f"  Creating ZK instance... OK")
        
        conn = zk.connect()
        print(f"  Connecting... OK")
        
        # Try to get device info
        firmware = conn.get_firmware_version()
        print(f"  Firmware: {firmware}")
        
        # Try to get user count
        users = conn.get_users()
        print(f"  Users: {len(users)}")
        
        # Try to get attendance count
        attendance = conn.get_attendance()
        print(f"  Attendance records: {len(attendance)}")
        
        conn.disconnect()
        print(f"  ✅ SUCCESS with {config['name']}")
        print(f"\n  Working parameters:")
        for key, value in config['params'].items():
            print(f"    {key}: {value}")
        
        sys.exit(0)  # Exit on first success
        
    except Exception as e:
        print(f"  ❌ FAILED: {str(e)}")
        continue

print("\n" + "=" * 60)
print("❌ All configurations failed!")
print("\nTroubleshooting:")
print("1. Check if device is powered on")
print("2. Verify IP address is correct (192.168.2.66)")
print("3. Check if port 4370 is open")
print("4. Try from TrueNAS host: telnet 192.168.2.66 4370")
print("5. Check device network settings")
