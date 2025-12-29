import threading
import time
from ble.ble import BLEHealthMonitor
from collector.collector import HealthDataCollector
from database.models import DatabaseManager

class BackgroundServiceManager:
    def __init__(self, db_path="data/sqlite.db"):
        self.db_manager = DatabaseManager(db_path=db_path)
        self.ble_scanner = BLEHealthMonitor()
        self.data_collector = HealthDataCollector(self.db_manager)
        self.background_threads = []
        self.is_running = False

    def _ble_worker(self):
        print("Starting BLE scanner...")
        while self.is_running:
            try:
                # Assuming ble_scanner has methods to manage scanning
                # accessing is_scanning property just to check state or similar
                _ = self.ble_scanner.is_scanning 
                time.sleep(10)
                self.ble_scanner.stop_continuous_scan()
                time.sleep(5)
            except Exception as e:
                print(f"BLE Scanner error: {e}")
                time.sleep(10)

    def _collector_worker(self):
        print("Starting data collector...")
        while self.is_running:
            try:
                self.data_collector.collect_ble_data(raw_data={})
                time.sleep(60)
            except Exception as e:
                print(f"Data Collector error: {e}")
                time.sleep(30)

    def start_services(self):
        if self.is_running:
            print("Services already running.")
            return

        self.is_running = True
        
        ble_thread = threading.Thread(target=self._ble_worker, daemon=True)
        collector_thread = threading.Thread(target=self._collector_worker, daemon=True)

        ble_thread.start()
        collector_thread.start()

        self.background_threads.extend([ble_thread, collector_thread])
        print("Background services started successfully")

    def stop_services(self):
        self.is_running = False
        print("Stopping background services...")
        # Threads are daemon, so they will exit when main process exits, 
        # but we set flag to stop loops if we want graceful shutdown
