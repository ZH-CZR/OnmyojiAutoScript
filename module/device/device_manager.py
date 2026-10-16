"""Share the scheduler's open device with config-only YYS task constructors."""
from threading import RLock


class DeviceManager:
    _devices = {}
    _lock = RLock()

    @classmethod
    def bind(cls, config, device):
        with cls._lock:
            cls._devices[config.config_name] = device

    @classmethod
    def get_device(cls, config=None):
        if config is None:
            raise ValueError("A script config is required to select a device")
        with cls._lock:
            if config.config_name not in cls._devices:
                from module.device.device import Device
                cls._devices[config.config_name] = Device(config=config)
            return cls._devices[config.config_name]

    @classmethod
    def get_device_status(cls, config=None):
        with cls._lock:
            return config.config_name in cls._devices if config is not None else bool(cls._devices)

    @classmethod
    def reset_device(cls, config=None):
        with cls._lock:
            names = [config.config_name] if config is not None else list(cls._devices)
            for name in names:
                device = cls._devices.pop(name, None)
                if device is not None:
                    device.release_during_wait()
