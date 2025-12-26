"""
Quick test script to verify DeviceSettings functionality
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spti_payroll.settings')
django.setup()

from attendance.models import DeviceSettings

def test_device_settings():
    """Test DeviceSettings model"""
    print("=" * 60)
    print("Testing DeviceSettings Model")
    print("=" * 60)
    
    # Get or create settings
    settings = DeviceSettings.get_settings()
    
    print(f"\n[OK] DeviceSettings instance retrieved successfully")
    print(f"  - ID: {settings.pk}")
    print(f"  - Device IP: {settings.device_ip}")
    print(f"  - Device Port: {settings.device_port}")
    print(f"  - Timeout: {settings.timeout}s")
    print(f"  - Password: {settings.password}")
    print(f"  - Force UDP: {settings.force_udp}")
    print(f"  - Omit Ping: {settings.ommit_ping}")
    
    # Test singleton behavior
    print(f"\n[OK] Testing singleton behavior...")
    settings2 = DeviceSettings.get_settings()
    assert settings.pk == settings2.pk, "Multiple instances detected!"
    print(f"  - Confirmed: Only one instance exists (pk={settings.pk})")
    
    # Test update
    print(f"\n[OK] Testing update functionality...")
    original_ip = settings.device_ip
    settings.device_ip = "192.168.1.100"
    settings.save()
    
    # Retrieve again
    settings_updated = DeviceSettings.get_settings()
    assert settings_updated.device_ip == "192.168.1.100", "Update failed!"
    print(f"  - IP updated from {original_ip} to {settings_updated.device_ip}")
    
    # Restore original
    settings.device_ip = original_ip
    settings.save()
    print(f"  - IP restored to {original_ip}")
    
    print("\n" + "=" * 60)
    print("[OK] All tests passed!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        test_device_settings()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
