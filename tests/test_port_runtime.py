from copy import deepcopy
from datetime import datetime, timedelta
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from module.compat.config_migration import migrate_config
from module.config.config import Config
from module.config.config_model import ConfigModel
from module.device.device import Device
from module.device.device_manager import DeviceManager
from module.exception import GameStuckError
from tasks.base_task import BaseTask


def test_device_binding_isolated_between_configs():
    a, b = SimpleNamespace(config_name="a"), SimpleNamespace(config_name="b")
    da, db = Mock(), Mock()
    DeviceManager.bind(a, da)
    DeviceManager.bind(b, db)
    assert DeviceManager.get_device(a) is da
    assert DeviceManager.get_device(b) is db
    DeviceManager.reset_device(a)
    da.release_during_wait.assert_called_once()
    assert not DeviceManager.get_device_status(a)
    assert DeviceManager.get_device_status(b)
    DeviceManager.reset_device(b)


def test_progress_checkpoint_preserves_other_recent_disk_settings(monkeypatch):
    stored = json.loads(ConfigModel().model_dump_json())
    monkeypatch.setattr(ConfigModel, "read_json", staticmethod(lambda _: deepcopy(stored)))

    def save(_, data):
        stored.clear()
        stored.update(json.loads(json.dumps(data, default=str)))

    monkeypatch.setattr(ConfigModel, "write_json", staticmethod(save))
    config = Config("checkpoint_test")
    task = BaseTask(config, device=object())
    stored["evo_zone"]["scheduler"]["priority"] = 2
    task.save_progress_current_count("evo_zone.evo_zone_config.saved_count", 7)
    assert stored["evo_zone"]["scheduler"]["priority"] == 2
    assert stored["evo_zone"]["evo_zone_config"]["saved_count"] == 7
    assert ConfigModel(**stored).evo_zone.evo_zone_config.saved_count == 7


def test_shop_migration_does_not_treat_activity_config_as_shop():
    data = {"weekly_purchase": {"guild_store": {"enable": True}}, "rich_man": {"activity": True}, "running_task": "WeeklyPurchase"}
    result = migrate_config(data)
    assert result["rich_man"] == data["weekly_purchase"]
    assert result["running_task"] == "RichMan"
    assert "weekly_purchase" in data  # no caller-owned mutation
    assert "rich_man" not in migrate_config({"rich_man": {"activity": True}})


def test_upstream_restart_disables_error_restarts():
    result = ConfigModel(**{"restart": {"task_config": {"error_restart": False}}})
    assert result.restart.restart_config.error_restart_limit == 0
    assert result.restart.scheduler.enable


def test_upstream_port_is_normalized_and_license_key_is_not_persisted():
    model = ConfigModel(**{'script': {'device': {'serial': '16384', 'card_key': 'unused-test-value'}}})
    assert model.script.device.serial == '127.0.0.1:16384'
    assert 'card_key' not in model.model_dump_json()


def test_invitation_preferences_move_to_upstream_task_without_overwriting():
    model = ConfigModel(**{'global_game': {'emergency': {'friend_invitation': 'jade_and_food'}}})
    assert model.wanted_quests.emergency.friend_invitation == 'jade_sushi_food'
    model = ConfigModel(**{'global_game': {'emergency': {'friend_invitation': 'accept'}},
                           'wanted_quests': {'emergency': {'friend_invitation': 'reject'}}})
    assert model.wanted_quests.emergency.friend_invitation == 'reject'


def test_unimplemented_desktop_backend_fails_explicitly():
    with pytest.raises(ValueError, match='window_win32'):
        ConfigModel(**{'script': {'device_2': {'emulator_control': 'win32'}}})


def test_upstream_timeouts_are_honored_in_seconds():
    device = Device.__new__(Device)
    device.stuck_timer = Mock()
    device.stuck_timer_long = Mock()
    device.stuck_timer.current.return_value = 120
    device.stuck_record_add(timeout=600)
    device.stuck_timer.reset.assert_called_once()
    assert device.stuck_record_check() is False
    device.stuck_timer.current.return_value = 601
    device.app_is_running = Mock(return_value=True)
    with pytest.raises(GameStuckError):
        device.stuck_record_check()
    assert device.stuck_timeout is None


def test_scheduler_and_serialization_use_upstream_task_names(monkeypatch):
    monkeypatch.setattr(ConfigModel, "read_json", staticmethod(lambda _: {}))
    config = Config("scheduler_test")
    for value in config.model.__dict__.values():
        if hasattr(value, 'scheduler'):
            value.scheduler.enable = False
    config.guild_gift.scheduler.enable = True
    config.guild_gift.scheduler.next_run = datetime.now() - timedelta(seconds=1)
    config.update_scheduler()
    assert [task.command for task in config.pending_task] == ["GuildGift"]
    assert ConfigModel.type("rich_man") == "RichMan"
    ConfigModel(**json.loads(config.model.model_dump_json()))


def test_filter_keeps_core_order_and_new_upstream_tasks():
    from module.config.scheduler import TaskScheduler
    from tasks.Script.config_optimization import ScheduleRule
    from module.config.config import Function
    tasks = [Function('daily_trifles', {'scheduler': {'enable': True, 'next_run': '2023-01-01 00:00:00', 'priority': 5}}),
             Function('guild_gift', {'scheduler': {'enable': True, 'next_run': '2023-01-01 00:00:00', 'priority': 2}})]
    result = TaskScheduler.schedule(ScheduleRule.FILTER, tasks)
    assert [task.command for task in result] == ['DailyTrifles', 'GuildGift']


def test_closed_tasks_fail_before_accessing_device():
    from module.compat.capabilities import require_task
    from module.exception import RequestHumanTakeover
    for name in ('Hyakkiyakou', 'SwitchAccountMany', 'TongXinTeam'):
        with pytest.raises(RequestHumanTakeover):
            require_task(name)
    require_task('GuildGift')


def test_script_dispatch_binds_the_same_device_for_config_only_tasks(monkeypatch):
    import script
    scheduler = script.Script.__new__(script.Script)
    scheduler.config = SimpleNamespace(config_name='dispatch_test', global_game=SimpleNamespace(ocr=SimpleNamespace(save_ocr_log=False)))
    scheduler.device = Mock()
    scheduler._reset_task_runtime_outcome = Mock()
    task = Mock()
    task_module = SimpleNamespace(ScriptTask=Mock(return_value=task))
    monkeypatch.setattr(script, 'load_module', Mock(return_value=task_module))
    monkeypatch.setattr(script, 'set_ocr_logging_enabled', Mock())
    scheduler.run('GuildGift')
    task_module.ScriptTask.assert_called_once_with(config=scheduler.config)
    task.run.assert_called_once()
    assert DeviceManager.get_device(scheduler.config) is scheduler.device
    DeviceManager.reset_device(scheduler.config)


def test_legacy_updaters_delegate_to_project_update(monkeypatch):
    from module.server.updater import Updater
    from deploy.git import GitManager
    from deploy import project_update
    project = Mock(message='更新已停止')
    project.fetch.return_value = False
    project.update.return_value = False
    factory = Mock(return_value=project)
    monkeypatch.setattr(project_update, 'ProjectUpdater', factory)
    updater = Updater.__new__(Updater)
    updater.execute = Mock()
    updater.execute_command = Mock()
    assert updater.fetch_remote() is False
    assert updater.execute_pull() is False
    updater.execute.assert_not_called()
    updater.execute_command.assert_not_called()
    installer = GitManager()
    installer.git_repository_init = Mock()
    installer.git_install()
    installer.git_repository_init.assert_not_called()
    project.fetch.assert_called_once()
    assert project.update.call_count == 2
