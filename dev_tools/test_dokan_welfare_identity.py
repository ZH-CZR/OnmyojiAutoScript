"""福利寮名单及加入已有道馆的识别，不连接设备或OCR服务。"""
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tasks.Dokan.script_task import ScriptTask


class DokanWelfareIdentityTests(unittest.TestCase):
    def make_task(self):
        task = object.__new__(ScriptTask)
        task.welfare_names = ['破晓', '甜心斗鱼姜', 'M78']
        task.open_welfare = False
        task.device = Mock(image=object())
        task.screenshot = Mock()
        task.has_welfare_badge = Mock(return_value=False)
        return task

    def test_shipped_list_contains_reported_guild(self):
        task = self.make_task()
        task.welfare_names = task.welfare_name_str()
        self.assertTrue(task.is_welfare_name('破晓'))

    def test_every_imported_spreadsheet_name_is_recognized(self):
        task = self.make_task()
        task.welfare_names = task.welfare_name_str()
        path = Path(__file__).resolve().parents[1] / 'upstream/dokan_welfare_names.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        for source in manifest['sources']:
            for record in source['records']:
                with self.subTest(file=source['file'], sheet=source['sheet'], cell=record['cell']):
                    self.assertTrue(task.is_welfare_name(record['name']))
        self.assertEqual(len(task.welfare_names), len(set(task.welfare_names)))
        for label in ('平均', '寮名', '人数', '赏金', '300以下', '100-300'):
            self.assertFalse(task.is_welfare_name(label))
        self.assertTrue(task.is_welfare_name('背水一战1'))
        self.assertTrue(task.is_welfare_name('M78'))

    def test_normalizes_whitespace_and_width_but_not_similar_names(self):
        task = self.make_task()
        for name in ('破 晓', ' 甜心斗鱼姜\n', 'Ｍ７８', '三涂鑫鑫子'):
            self.assertTrue(task.is_welfare_name(name))
        for name in ('', None, '破晓之光', '破晚', '甜心斗鱼', '普通寮'):
            self.assertFalse(task.is_welfare_name(name))
        task.welfare_names = None
        self.assertFalse(task.is_welfare_name('破晓'))

    def test_two_fresh_map_name_reads_confirm_welfare(self):
        task = self.make_task()
        with patch('tasks.Dokan.script_task.RuleOcr') as rule, \
                patch('tasks.Dokan.script_task.time.sleep') as sleep:
            rule.return_value.ocr.side_effect = ['甜心斗鱼姜', '甜心斗鱼姜']
            task.identify_joined_welfare((353, 304, 66, 28))
        self.assertTrue(task.open_welfare)
        self.assertEqual(rule.call_args.kwargs['roi'], (256, 332, 260, 45))
        sleep.assert_called_once_with(0.35)
        task.screenshot.assert_called_once()

    def test_unknown_or_inconsistent_name_does_not_confirm_welfare(self):
        for names in (['普通寮'], ['破晓', '普通寮'], ['破晓', '甜心斗鱼姜']):
            task = self.make_task()
            with patch('tasks.Dokan.script_task.RuleOcr') as rule, \
                    patch('tasks.Dokan.script_task.time.sleep'):
                rule.return_value.ocr.side_effect = names
                task.identify_joined_welfare((353, 304, 66, 28))
            self.assertFalse(task.open_welfare)

    def test_invalid_name_area_does_not_run_ocr(self):
        task = self.make_task()
        for box in ((100, 710, 20, 20), (1250, 100, 30, 20), (100, 100, 0, 20)):
            with patch('tasks.Dokan.script_task.RuleOcr') as rule:
                task.identify_joined_welfare(box)
            rule.assert_not_called()
        self.assertFalse(task.open_welfare)

    def test_join_confirms_identity_before_soul_switch(self):
        task = self.make_task()
        task.is_in_dokan = Mock(side_effect=[False, True])
        task.appear = Mock(return_value=False)
        task.O_DOKAN_MAP = SimpleNamespace(ocr_full=Mock(return_value=(353, 304, 66, 28)))
        flags = []
        task.dokan_switch_soul = Mock(side_effect=lambda: flags.append(task.open_welfare))
        with patch('tasks.Dokan.script_task.RuleOcr') as rule, \
                patch('tasks.Dokan.script_task.time.sleep'):
            rule.return_value.ocr.side_effect = ['破晓', '破晓']
            task.goto_dokan_click()
        self.assertEqual(flags, [True])
        task.device.click.assert_called_once_with(x=386, y=284)


if __name__ == '__main__':
    unittest.main()
