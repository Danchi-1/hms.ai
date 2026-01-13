import asyncio
import logging
from bleak import BleakScanner, BleakClient
from datetime import datetime
import json
import threading
import time
from typing import Dict, List, Optional, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BLEHealthMonitor:
    """
    Bluetooth Low Energy health device scanner and data collector
    Supports common health devices like heart rate monitors, fitness trackers, etc.
    """
    
    # Common health device service UUIDs
    HEALTH_SERVICES = {
        'heart_rate': '0000180d-0000-1000-8000-00805f9b34fb',
        'fitness_machine': '00001826-0000-1000-8000-00805f9b34fb',
        'body_composition': '0000181b-0000-1000-8000-00805f9b34fb',
        'weight_scale': '0000181d-0000-1000-8000-00805f9b34fb',
        'blood_pressure': '00001810-0000-1000-8000-00805f9b34fb',
        'glucose': '00001808-0000-1000-8000-00805f9b34fb'
    }
    
    # Common characteristic UUIDs
    CHARACTERISTICS = {
        'heart_rate_measurement': '00002a37-0000-1000-8000-00805f9b34fb',
        'body_sensor_location': '00002a38-0000-1000-8000-00805f9b34fb',
        'battery_level': '00002a19-0000-1000-8000-00805f9b34fb',
        'device_name': '00002a00-0000-1000-8000-00805f9b34fb',
        'manufacturer_name': '00002a29-0000-1000-8000-00805f9b34fb'
    }
    
    def __init__(self, data_callback: Optional[Callable] = None):
        self.data_callback = data_callback
        self.connected_devices: Dict[str, BleakClient] = {}
        self.device_info: Dict[str, Dict] = {}
        self.is_scanning = False
        self.is_monitoring = False
        self.scan_thread = None
        self.monitor_thread = None
        
    async def scan_for_devices(self, duration: int = 10, filter_strict: bool = True) -> List[Dict]:
        """
        Scan for BLE health devices
        
        Args:
            duration: Scan duration in seconds
            filter_strict: If True, only return devices matching specific health keywords or services
            
        Returns:
            List of discovered health devices
        """
        logger.info(f"Scanning for BLE health devices for {duration} seconds (strict_mode={filter_strict})...")
        
        try:
            # We need advertisement data to utilize UUID filtering effectively without connecting
            # returning_adv=True returns a dict of {address: (device, advertisement_data)}
            devices_dict = await BleakScanner.discover(timeout=duration, return_adv=True)
        except (Exception, OSError) as e:
            logger.warning(f"Bluetooth scanning failed (likely no hardware): {e}")
            return []
        health_devices = []
        
        for address, (device, adv_data) in devices_dict.items():
            if self._is_health_device(device, adv_data, filter_strict):
                device_info = {
                    'name': device.name or "Unknown Device",
                    'address': device.address,
                    'rssi': device.rssi,
                    'services': list(adv_data.service_uuids) if adv_data.service_uuids else [],
                    'device_type': self._identify_device_type(device, adv_data),
                    'discovered_at': datetime.now().isoformat()
                }
                
                # Note: We don't connect here to get services as it's slow and disruptive during scan
                # We rely on advertised services
                
                health_devices.append(device_info)
                logger.info(f"Found health device: {device_info['name']} ({device.address})")
            else:
                logger.debug(f"Skipping non-health device: {device.name} ({device.address})")
        
        # Sort by RSSI (descending) - strongest signal first
        health_devices.sort(key=lambda x: x.get('rssi', -100), reverse=True)
        return health_devices
    
    def _is_health_device(self, device, adv_data, strict: bool = True) -> bool:
        """
        Check if device is a health/fitness device
        
        Args:
            device: BLEDevice object
            adv_data: AdvertisementData object
            strict: If True, enforces strict name/UUID matching
        """
        # If strict mode is off, accept any device with a name
        if not strict:
            return True if device.name else False
            
        # 1. Check Service UUIDs (Strongest indicator)
        if adv_data.service_uuids:
            for uuid in adv_data.service_uuids:
                if str(uuid) in self.HEALTH_SERVICES.values():
                    return True
                    
        # 2. Check Name Patterns
        if device.name:
            health_keywords = [
                'heart', 'polar', 'garmin', 'fitbit', 'apple',
                'samsung', 'withings', 'omron', 'scale', 'blood',
                'glucose', 'pulse', 'fitness', 'tracker', 'band',
                'watch', 'mi', 'honor', 'huawei', 'amazfit', 'ring',
                'oura', 'whoop', 'smart'
            ]
            
            device_name_lower = device.name.lower()
            return any(keyword in device_name_lower for keyword in health_keywords)
            
        return False
    
    def _identify_device_type(self, device, adv_data=None) -> str:
        """Identify the type of health device"""
        
        # Check Service UUIDs first if available
        if adv_data and adv_data.service_uuids:
            uuids = [str(u) for u in adv_data.service_uuids]
            if self.HEALTH_SERVICES['heart_rate'] in uuids:
                return 'heart_rate_monitor'
            if self.HEALTH_SERVICES['weight_scale'] in uuids or self.HEALTH_SERVICES['body_composition'] in uuids:
                return 'weight_scale'
            if self.HEALTH_SERVICES['blood_pressure'] in uuids:
                return 'blood_pressure_monitor'
            if self.HEALTH_SERVICES['glucose'] in uuids:
                return 'glucose_meter'

        if not device.name:
            return 'unknown_health_device'
            
        name_lower = device.name.lower()
        
        if any(word in name_lower for word in ['heart', 'hr', 'pulse', 'polar']):
            return 'heart_rate_monitor'
        elif any(word in name_lower for word in ['scale', 'weight']):
            return 'weight_scale'
        elif any(word in name_lower for word in ['blood', 'pressure', 'bp']):
            return 'blood_pressure_monitor'
        elif any(word in name_lower for word in ['glucose', 'sugar', 'diabetes']):
            return 'glucose_meter'
        elif any(word in name_lower for word in ['fitbit', 'garmin', 'tracker', 'band', 'watch', 'ring']):
            return 'fitness_tracker'
        else:
            return 'health_device'
    
    async def connect_to_device(self, device_address: str) -> bool:
        """
        Connect to a specific BLE device
        
        Args:
            device_address: MAC address of the device
            
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to device: {device_address}")
            
            client = BleakClient(device_address)
            await client.connect()
            
            if client.is_connected:
                self.connected_devices[device_address] = client
                
                # Get device info
                device_info = await self._get_device_info(client)
                self.device_info[device_address] = device_info
                
                logger.info(f"Successfully connected to {device_info.get('name', device_address)}")
                return True
            else:
                logger.error(f"Failed to connect to {device_address}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to {device_address}: {e}")
            return False
    
    async def _get_device_info(self, client: BleakClient) -> Dict:
        """Get detailed information about connected device"""
        info = {
            'address': client.address,
            'connected_at': datetime.now().isoformat(),
            'services': [],
            'characteristics': []
        }
        
        try:
            services = await client.get_services() # type: ignore[attr-defined]
            
            for service in services:
                service_info = {
                    'uuid': str(service.uuid),
                    'description': service.description,
                    'characteristics': []
                }
                
                for char in service.characteristics:
                    char_info = {
                        'uuid': str(char.uuid),
                        'properties': char.properties,
                        'descriptors': [str(desc.uuid) for desc in char.descriptors]
                    }
                    service_info['characteristics'].append(char_info)
                    info['characteristics'].append(char_info)
                
                info['services'].append(service_info)
            
            # Try to read device name
            try:
                name_char = self.CHARACTERISTICS['device_name']
                if any(char['uuid'] == name_char for char in info['characteristics']):
                    name_data = await client.read_gatt_char(name_char)
                    info['name'] = name_data.decode('utf-8')
            except:
                pass
            
            # Try to read manufacturer
            try:
                manufacturer_char = self.CHARACTERISTICS['manufacturer_name']
                if any(char['uuid'] == manufacturer_char for char in info['characteristics']):
                    manufacturer_data = await client.read_gatt_char(manufacturer_char)
                    info['manufacturer'] = manufacturer_data.decode('utf-8')
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
        
        return info
    
    async def start_monitoring(self, device_address: str) -> bool:
        """
        Start monitoring health data from connected device
        
        Args:
            device_address: MAC address of the device
            
        Returns:
            True if monitoring started successfully
        """
        if device_address not in self.connected_devices:
            logger.error(f"Device {device_address} not connected")
            return False
        
        client = self.connected_devices[device_address]
        device_info = self.device_info.get(device_address, {})
        
        try:
            # Start monitoring based on device type
            if self._has_heart_rate_service(device_info):
                await self._start_heart_rate_monitoring(client, device_address)
            
            # Add more monitoring types as needed
            # if self._has_weight_service(device_info):
            #     await self._start_weight_monitoring(client, device_address)
            
            self.is_monitoring = True
            logger.info(f"Started monitoring {device_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting monitoring for {device_address}: {e}")
            return False
    
    def _has_heart_rate_service(self, device_info: Dict) -> bool:
        """Check if device has heart rate service"""
        hr_service = self.HEALTH_SERVICES['heart_rate']
        return any(service['uuid'] == hr_service for service in device_info.get('services', []))
    
    async def _start_heart_rate_monitoring(self, client: BleakClient, device_address: str):
        """Start heart rate monitoring"""
        hr_char = self.CHARACTERISTICS['heart_rate_measurement']
        
        def heart_rate_callback(sender, data):
            """Callback for heart rate data"""
            heart_rate = self._parse_heart_rate_data(data)
            
            health_data = {
                'device_address': device_address,
                'device_type': 'heart_rate_monitor',
                'measurement_type': 'heart_rate',
                'value': heart_rate,
                'timestamp': datetime.now().isoformat(),
                'raw_data': data.hex()
            }
            
            logger.info(f"Heart rate: {heart_rate} BPM")
            
            # Send to callback if available
            if self.data_callback:
                self.data_callback(health_data)
        
        # Start notifications
        await client.start_notify(hr_char, heart_rate_callback)
        logger.info("Heart rate monitoring started")
    
    def _parse_heart_rate_data(self, data: bytes) -> int:
        """Parse heart rate measurement data"""
        # Heart rate measurement format (simplified)
        # First byte contains flags, second byte contains heart rate
        if len(data) >= 2:
            flags = data[0]
            if flags & 0x01:  # 16-bit heart rate
                return int.from_bytes(data[1:3], byteorder='little')
            else:  # 8-bit heart rate
                return data[1]
        return 0
    
    async def disconnect_device(self, device_address: str):
        """Disconnect from a specific device"""
        if device_address in self.connected_devices:
            client = self.connected_devices[device_address]
            try:
                await client.disconnect()
                logger.info(f"Disconnected from device {device_address}")
            except Exception as e:
                logger.error(f"Error disconnecting from {device_address}: {e}")
            finally:
                del self.connected_devices[device_address]
                if device_address in self.device_info:
                    del self.device_info[device_address]
        else:
            logger.warning(f"Device {device_address} not connected")

    
    async def disconnect_all(self):
        """Disconnect from all connected devices"""
        for address in list(self.connected_devices.keys()):
            await self.disconnect_device(address)
        self.is_monitoring = False
    
    def start_continuous_scan(self, callback: Optional[Callable] = None):
        """Start continuous scanning in background thread"""
        self.is_scanning = True
        
        def scan_worker():
            while self.is_scanning:
                try:
                    devices = asyncio.run(self.scan_for_devices(duration=10))
                    if callback:
                        callback(devices)
                    time.sleep(30)  # Wait 30 seconds between scans
                except Exception as e:
                    logger.error(f"Error in continuous scan: {e}")
                    time.sleep(60)  # Wait longer on error
        
        self.scan_thread = threading.Thread(target=scan_worker)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        logger.info("Started continuous BLE scanning")
    
    def stop_continuous_scan(self):
        """Stop continuous scanning"""
        self.is_scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=5)
        logger.info("Stopped continuous BLE scanning")
    
    def get_connected_devices(self) -> List[Dict]:
        """Get list of currently connected devices"""
        return [
            {
                'address': address,
                'info': self.device_info.get(address, {}),
                'connected': client.is_connected
            }
            for address, client in self.connected_devices.items()
        ]

# Example usage and testing
async def main():
    """Example usage of BLE Health Monitor"""
    
    def data_handler(health_data):
        """Handle incoming health data"""
        logger.info(f"Recieved health data: {health_data}")
    
    monitor = BLEHealthMonitor(data_callback=data_handler)
    
    # Scan for devices
    print("Scanning for health devices...")
    devices = await monitor.scan_for_devices(duration=15)
    
    if devices:
        print(f"\nFound {len(devices)} health devices:")
        for device in devices:
            print(f"- {device['name']} ({device['address']}) - {device['device_type']}")
        
        # Connect to first device (if any)
        first_device = devices[0]
        success = await monitor.connect_to_device(first_device['address'])
        
        if success:
            print(f"\nConnected to {first_device['name']}")
            
            # Start monitoring
            await monitor.start_monitoring(first_device['address'])
            
            # Monitor for 30 seconds
            print("Monitoring for 30 seconds...")
            await asyncio.sleep(30)
            
            # Disconnect
            await monitor.disconnect_all()
            print("Disconnected from all devices")
    else:
        print("No health devices found")
    return devices

if __name__ == "__main__":
    asyncio.run(main())