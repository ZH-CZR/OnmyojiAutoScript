"""YYS-facing facade backed by the public OAS emulator implementation."""
from module.device.device_manager import DeviceManager


class EmulatorManager:
    def __init__(self, config):
        self.config = config

    @property
    def device(self):
        return DeviceManager.get_device(self.config)

    def is_emulator_running(self):
        return self.device.adb.get_state() == "device"

    def start_emulator(self):
        return self.device.emulator_start()

    def stop_emulator(self):
        return self.device.emulator_stop()

    def app_start(self):
        return self.device.app_start()

    def app_stop(self):
        return self.device.app_stop()

    def is_app_running(self):
        return self.device.app_is_running()
