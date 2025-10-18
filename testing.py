from bleak import BleakScanner
import asyncio

async def scan(timeout=10):
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=timeout)
    for d in devices:
        print(f"Device: {d.name}, Address: {d.address}, Metadata: {d.details}\n")
    return devices

ble_devices = asyncio.run(scan())
print(f"Found devices: {ble_devices}")