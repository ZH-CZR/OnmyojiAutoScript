# This Python file uses the following encoding: utf-8
# copy from alas https://github.com/LmeSzinc/AzurLaneAutoScript
import copy
from typing import Optional, Union

from deploy.logger import logger
from deploy.utils import *


class ConfigModel:
    # Project updates (origin/master of this fork only)
    AutoUpdate: bool = False
    CheckUpdateInterval: int = 5
    AutoRestartTime: Optional[str] = None

    # Device connection
    AdbExecutable: str = "./toolkit/Lib/site-packages/adbutils/binaries/adb.exe"

    # Ocr
    StartOcrServer: bool = True
    OcrServerPort: int = 22268
    OcrClientAddress: str = "127.0.0.1:22268"
    OcrServerWorkerCount: int = 0

    # Image
    StartImageServer: bool = True
    ImageServerPort: int = 22269
    ImageClientAddress: str = "127.0.0.1:22269"
    ImageTemplateCacheExpireSeconds: int = 3600
    ImageTemplateCacheMaxCount: int = 200
    ImageFrameCacheExpireSeconds: float = 10.0
    ImageFrameCacheMaxCount: int = 66
    ImageServerWorkerCount: int = 0

    # Misc
    DiscordRichPresence: bool = False

    # Remote Access
    EnableRemoteAccess: bool = False
    SSHUser: Optional[str] = None
    SSHServer: Optional[str] = None
    SSHExecutable: Optional[str] = None

    # Webui
    WebuiHost: str = "0.0.0.0"
    WebuiPort: int = 22267
    Language: str = "en-US"
    Theme: str = "default"
    DpiScaling: bool = True
    Password: Optional[str] = None
    CDN: Union[str, bool] = False
    Run: Optional[str] = None


class DeployConfig(ConfigModel):
    def __init__(self, file=DEPLOY_CONFIG):
        """
        Args:
            file (str): User deploy config.
        """
        self.file = file
        self.config = {}
        self.read()

    def show_config(self):
        logger.hr("Show deploy config", 1)
        for k, v in self.config.items():
            if k in ("Password", "SSHUser"):
                continue
            if self.config_template[k] == v:
                continue
            logger.info(f"{k}: {v}")

        logger.info(f"Rest of the configs are the same as default")

    def read(self):
        self.config = poor_yaml_read(DEPLOY_TEMPLATE)
        self.config_template = copy.deepcopy(self.config)
        self.config.update(poor_yaml_read(self.file))
        unknown_keys = [key for key in list(self.config.keys()) if not hasattr(self, key)]
        for key in unknown_keys:
            logger.warning(f"Ignore deprecated deploy config key: {key}")
            self.config.pop(key, None)

        for key, value in self.config.items():
            if hasattr(self, key):
                super().__setattr__(key, value)

    def write(self):
        poor_yaml_write(self.config, self.file)

    def filepath(self, key):
        """
        Args:
            key (str):

        Returns:
            str: Absolute filepath.
        """
        return (
            os.path.abspath(os.path.join(self.root_filepath, self.config[key]))
            .replace(r"\\", "/")
            .replace("\\", "/")
            .replace('"', '"')
        )

    @cached_property
    def root_filepath(self):
        return (
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
            .replace(r"\\", "/")
            .replace("\\", "/")
            .replace('"', '"')
        )
