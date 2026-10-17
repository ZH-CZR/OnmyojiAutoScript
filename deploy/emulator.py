import os
import re
import winreg

from deploy.utils import cached_property



class VirtualBoxEmulator:
    UNINSTALL_REG = "SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
    UNINSTALL_REG_2 = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall"

    def __init__(self, name, root_path, adb_path, vbox_path, vbox_name):
        """
        Args:
            name (str): Emulator name in windows uninstall list.
            root_path (str): Relative path from uninstall.exe to emulator installation folder.
            adb_path (str, list[str]): Relative path to adb.exe. List of str if there are multiple adb in emulator.
            vbox_path (str): Relative path to virtual box folder.
            vbox_name (str): Regular Expression to match the name of .vbox file.
        """
        self.name = name
        self.root_path = root_path
        self.adb_path = adb_path if isinstance(adb_path, list) else [adb_path]
        self.vbox_path = vbox_path
        self.vbox_name = vbox_name

    @cached_property
    def root(self):
        """
        Returns:
            str: Root installation folder of emulator.

        Raises:
            FileNotFoundError: If emulator not installed.
        """
        if self.name == 'LDPlayer4':
            root = self.get_install_dir_from_reg('SOFTWARE\\leidian\\ldplayer', 'InstallDir')
            if root is not None:
                return root
        if self.name == 'LDPlayer9':
            root = self.get_install_dir_from_reg('SOFTWARE\\leidian\\ldplayer9', 'InstallDir')
            if root is not None:
                return root

        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'{self.UNINSTALL_REG}\\{self.name}', 0)
        except FileNotFoundError:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f'{self.UNINSTALL_REG_2}\\{self.name}', 0)
        res = winreg.QueryValueEx(reg, 'UninstallString')[0]

        file = re.search('"(.*?)"', res)
        file = file.group(1) if file else res
        root = os.path.abspath(os.path.join(os.path.dirname(file), self.root_path))
        return root

    def get_install_dir_from_reg(self, path, key):
        """
        Args:
            path (str): f'SOFTWARE\\leidian\\ldplayer'
            key (str): 'InstallDir'

        Returns:
            str: Installation dir or None
        """
        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0)
            root = winreg.QueryValueEx(reg, key)[0]
            if os.path.exists(root):
                return root
        except FileNotFoundError:
            pass
        try:
            reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0)
            root = winreg.QueryValueEx(reg, key)[0]
            if os.path.exists(root):
                return root
        except FileNotFoundError:
            pass

        return None

    @cached_property
    def adb_binary(self):
        return [os.path.abspath(os.path.join(self.root, a)) for a in self.adb_path]

    @cached_property
    def serial(self):
        """
        Returns:
            list[str]: Such as ['127.0.0.1:62001', '127.0.0.1:62025']
        """
        vbox = []
        for path, folders, files in os.walk(os.path.join(self.root, self.vbox_path)):
            for file in files:
                if re.match(self.vbox_name, file):
                    file = os.path.join(path, file)
                    vbox.append(file)

        serial = []
        for file in vbox:
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f.readlines():
                    # <Forwarding name="port2" proto="1" hostip="127.0.0.1" hostport="62026" guestport="5555"/>
                    res = re.search('<*?hostport="(.*?)".*?guestport="5555"/>', line)
                    if res:
                        serial.append(f'127.0.0.1:{res.group(1)}')

        return serial
