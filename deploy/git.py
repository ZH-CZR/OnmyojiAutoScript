# Originally copied from https://github.com/LmeSzinc/AzurLaneAutoScript
# Shared safe updater for the legacy installer and the web service.
from deploy.config import DeployConfig, ExecutionError
from deploy.logger import logger
from deploy.project_update import ProjectUpdater
from deploy.utils import cached_property


class GitManager(DeployConfig):
    @cached_property
    def git(self):
        return self.filepath('GitExecutable')

    def project_updater(self):
        return ProjectUpdater(self.root_filepath, self.git,
                              repository=self.Repository, branch=self.Branch,
                              git_proxy=self.GitProxy, ssl_verify=self.SSLVerify)

    def git_install(self, *, service_owned=False):
        if not self.AutoUpdate:
            logger.info('Automatic installation is disabled')
            return
        installer = self.pip_install if self.InstallDependencies else None
        result = self.project_updater().install(installer, service_owned=service_owned)
        logger.info(result['message'])
        if result['status'] not in ('updated', 'up_to_date'):
            raise ExecutionError
