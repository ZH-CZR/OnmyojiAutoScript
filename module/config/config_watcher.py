# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import os
from module.config.utils import filepath_config
from module.logger import logger

class ConfigWatcher:
    """
    监视特定配置文件修改的功能。
    它跟踪了初始修改时间,(start_mtime)
    并提供了方法来检查文件是否被修改(should_reload)
    和获取当前修改时间(get_mtime)。
    """
    config_name = 'script'
    start_mtime = None

    def start_watching(self) -> None:
        # Keep the stamp from BEFORE loading the model. A save between loading
        # and beginning the idle wait must also interrupt that wait.
        if '_loaded_mtime' in self.__dict__:
            self.start_mtime = self.__dict__['_loaded_mtime']
        else:
            self.start_mtime = self.get_mtime()

    def get_mtime(self) -> tuple | None:
        """
        Last modify time of the file
        """
        try:
            stat = os.stat(filepath_config(self.config_name))
        except FileNotFoundError:
            return None
        return stat.st_dev, stat.st_ino, stat.st_mtime_ns, stat.st_size

    def should_reload(self) -> bool:
        """
        Returns:
            bool: Whether the file has been modified and configs should reload
        """
        mtime = self.get_mtime()
        if mtime != self.start_mtime:
            logger.info(f'Config "{self.config_name}" changed at {mtime}')
            return True
        else:
            return False

