import asyncio
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ble.ble import BLEHealthMonitor

async def test_ble_scanning():
    print("Testing BLE Scanning Logic adjustment...")
    
    # Mock data
    mock_device_health = MagicMock()
    mock_device_health.name = "Unknown Gadget 3000"
    mock_device_health.address = "AA:BB:CC:DD:EE:FF"
    mock_device_health.rssi = -60

    mock_adv_health = MagicMock()
    mock_adv_health.service_uuids = ['0000180d-0000-1000-8000-00805f9b34fb'] # Heart Rate UUID
    
    mock_device_junk = MagicMock()
    mock_device_junk.name = "My TV"
    mock_device_junk.address = "11:22:33:44:55:66"
    mock_device_junk.rssi = -80
    
    mock_adv_junk = MagicMock()
    mock_adv_junk.service_uuids = []

    # Mock discover return value
    # Format: {address: (device, adv_data)}
    mock_discover_result = {
        mock_device_health.address: (mock_device_health, mock_adv_health),
        mock_device_junk.address: (mock_device_junk, mock_adv_junk)
    }

    with patch('ble.ble.BleakScanner.discover', new_callable=MagicMock) as mock_discover:
        mock_discover.return_value = mock_discover_result
        
        scanner = BLEHealthMonitor()
        
        # Test 1: Strict Mode (Should still find the Unknown Gadget because of UUID)
        print("\n--- Test 1: Scan with strict=True (Default) ---")
        devices = await scanner.scan_for_devices(duration=1)
        
        print(f"Found {len(devices)} devices:")
        found_address = [d['address'] for d in devices]
        for d in devices:
            print(f"- {d['name']} ({d['address']}) Type: {d['device_type']}")
            
        if mock_device_health.address in found_address:
            print("PASS: Found device with Heart Rate UUID despite unknown name.")
        else:
            print("FAIL: Did not find health device.")
            
        if mock_device_junk.address not in found_address:
            print("PASS: Ignored junk device.")
        else:
            print("FAIL: Found junk device in strict mode.")

        # Test 2: Relaxed Mode
        print("\n--- Test 2: Scan with strict=False ---")
        devices_relaxed = await scanner.scan_for_devices(duration=1, filter_strict=False)
        found_address_relaxed = [d['address'] for d in devices_relaxed]
        
        if mock_device_junk.address in found_address_relaxed:
            print("PASS: Found junk device in relaxed mode.")
        else:
            print("FAIL: Did not find junk device in relaxed mode.")

if __name__ == "__main__":
    asyncio.run(test_ble_scanning())
