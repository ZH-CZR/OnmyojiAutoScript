from pathlib import Path

import pytest

from dev_tools.upstream_policy import selected, adapt
from dev_tools.upstream_sync import digest, normalized_digest, plan_update


def record(data):
    return {"installed_sha256": digest(data)}


def test_selection_excludes_native_licensing_and_keeps_public_six_realms():
    for name in ("script.cp310-win_amd64.pyd", "deploy/Identity.py", "module/device/control.py",
                 "tasks/TongXinTeam/script_task.py", "tasks/SwitchAccountMany/script_task.py",
                 "tasks/Component/SwitchAccount/login_account_many.py", "tasks/Hyakkiyakou/agent/agent.py"):
        assert not selected(name)
    assert selected("tasks/SixRealms_jue/moon_sea/skills.py")
    assert selected("tasks/GuildGift/script_task.py")


def test_opaque_python_is_rejected():
    with pytest.raises(ValueError, match="Opaque code"):
        adapt("tasks/GuildGift/script_task.py", b"import marshal\nmarshal.loads(payload)", "")


def test_upstream_interface_drift_stops_before_import():
    with pytest.raises(ValueError, match="interface changed"):
        adapt("tasks/base_task_parent.py", b"class NewBaseTask: pass", "")


def test_traversal_is_rejected():
    with pytest.raises(ValueError):
        selected("tasks/../../escape.py")


def test_local_edits_deletions_and_collisions_are_conflicts(tmp_path):
    (tmp_path / "edited.py").write_bytes(b"local")
    (tmp_path / "new.py").write_bytes(b"local")
    previous = {"edited.py": record(b"old"), "deleted.py": record(b"old")}
    actions, conflicts = plan_update(tmp_path, {"edited.py": b"upstream", "deleted.py": b"upstream", "new.py": b"upstream"}, previous, {})
    assert actions == []
    assert conflicts == ["deleted.py", "edited.py", "new.py"]
    assert (tmp_path / "edited.py").read_bytes() == b"local"


def test_update_add_delete_and_idempotence(tmp_path):
    (tmp_path / "update.py").write_bytes(b"old")
    (tmp_path / "delete.py").write_bytes(b"old")
    (tmp_path / "same.py").write_bytes(b"same")
    rendered = {"update.py": b"new", "new.py": b"new", "same.py": b"same"}
    previous = {name: record(data) for name, data in (("update.py", b"old"), ("delete.py", b"old"), ("same.py", b"same"))}
    actions, conflicts = plan_update(tmp_path, rendered, previous, {})
    assert not conflicts
    assert dict(actions) == {"delete.py": None, "new.py": b"new", "update.py": b"new"}
    for name, data in actions:
        if data is None:
            (tmp_path / name).unlink()
        else:
            (tmp_path / name).write_bytes(data)
    assert plan_update(tmp_path, rendered, {n: record(d) for n, d in rendered.items()}, {}) == ([], [])


def test_git_crlf_checkouts_do_not_create_false_conflicts(tmp_path):
    (tmp_path / "task.json").write_bytes(b'{\r\n"value": 1\r\n}')
    old = b'{\n"value": 1\n}'
    assert plan_update(tmp_path, {"task.json": b"new"}, {}, {"task.json": old}) == ([("task.json", b"new")], [])


def test_target_outside_checkout_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        plan_update(tmp_path, {"../outside.py": b"bad"}, {}, {})


def test_directory_collision_is_reported_during_preflight(tmp_path):
    (tmp_path / 'task.py').mkdir()
    assert plan_update(tmp_path, {'task.py': b'new'}, {}, {}) == ([], ['task.py'])
