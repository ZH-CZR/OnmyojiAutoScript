from deploy.patch import pre_checks

pre_checks()

from deploy.adb import AdbManager
from deploy.process import ProcessManager
from deploy.fluentui import FluentuiManager
from deploy.config import ExecutionError
from deploy.git import GitManager
from deploy.pip import PipManager
from deploy.project_update import UpdateError


class Installer(GitManager, PipManager, AdbManager, FluentuiManager, ProcessManager):
    def install(self):
        try:
            updater = self.project_updater()
            with updater.lock('oas-service-runtime.lock'):
                self.git_install(service_owned=True)
                self.process_kill()
                # First installation or a recorded dependency change only.
                if updater.dependency_pending() or not updater.state_file.exists():
                    if not self.InstallDependencies:
                        if updater.dependency_pending():
                            raise ExecutionError('Dependencies pending; enable InstallDependencies')
                    else:
                        updater.mark_dependencies(True)
                        updater.complete_dependencies(self.pip_install)
                self.adb_install()
        except (ExecutionError, UpdateError) as exc:
            from deploy.logger import logger
            logger.error(str(exc) or 'Installation failed')
            exit(1)


if __name__ == '__main__':
    Installer().install()
