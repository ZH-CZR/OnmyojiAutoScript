from deploy.patch import pre_checks

pre_checks()

from deploy.adb import AdbManager
from deploy.process import ProcessManager
from deploy.fluentui import FluentuiManager
from deploy.config import ExecutionError
from deploy.git import GitManager
from deploy.pip import PipManager
from deploy.project_update import UpdateError
from deploy.first_run import runtime_lock
from deploy.logger import logger


class Installer(GitManager, PipManager, AdbManager, FluentuiManager, ProcessManager):
    def install(self):
        try:
            updater = self.project_updater()
            if updater.is_source_archive():
                with runtime_lock(updater.git, root=updater.root):
                    logger.info('源码安装：保留文件；代码更新仅在后端启动时检查')
                    if self.InstallDependencies:
                        self.pip_install()
                    self.adb_install()
                return
            with updater.lock('oas-service-runtime.lock'):
                # Frontends may run this before server.py. Do not fetch/install
                # code here or terminate processes; server startup owns updating.
                # First installation or a recorded dependency change only.
                if updater.dependency_pending() or not updater.state_file.exists():
                    if not self.InstallDependencies:
                        if updater.dependency_pending():
                            raise ExecutionError('Dependencies pending; enable InstallDependencies')
                    else:
                        updater.mark_dependencies(True)
                        updater.complete_dependencies(self.pip_install)
                self.adb_install()
        except (ExecutionError, UpdateError, RuntimeError) as exc:
            from deploy.logger import logger
            logger.error(str(exc) or 'Installation failed')
            exit(1)


if __name__ == '__main__':
    Installer().install()
