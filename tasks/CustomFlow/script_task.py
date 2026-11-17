# -*- coding: utf-8 -*-
"""通用流程任务：按 flows/<name>.json 解释执行，不需要为每个流程写 Python。

需要固定下来的流程可以在标注器里「生成代码」，它会把步骤展开成真正的
tasks/<Task>/script_task.py；本文件只是一条通用跑道。
"""
from module.exception import GameStuckError, TaskEnd
from module.flow.errors import FlowAbort, FlowEnd, FlowSchemaError
from module.flow.host import TaskFlowHost
from module.flow.rules import RuleLibrary
from module.flow.runtime import FlowRunner
from module.flow.store import FlowStore
from module.logger import logger
from tasks.CustomFlow.assets import CustomFlowAssets
from tasks.GameUi.game_ui import GameUi


class ScriptTask(GameUi, CustomFlowAssets):
    def run(self) -> None:
        name = str(self.config.custom_flow.flow.flow_name or "").strip()
        if not name:
            raise GameStuckError("CustomFlow 没有配置 flow_name（config/custom_flow.flow.flow_name）")

        store = FlowStore()
        try:
            flow = store.load(name)
        except FlowSchemaError as e:
            raise GameStuckError(f"流程 {name} 读取失败: {e}")

        task_name = str(flow.get("task") or "CustomFlow")
        rules = RuleLibrary(task_name)
        runner = FlowRunner(TaskFlowHost(self, rules), flow)
        logger.hr(f"CustomFlow: {name}", level=2)
        try:
            runner.run()
        except FlowEnd as e:
            if not self.config.custom_flow.flow.stop_after_end:
                self.set_next_run(task="CustomFlow", success=e.success, finish=False)
            raise TaskEnd
        except FlowAbort as e:
            logger.error(f"流程 {name} 中断: {e}")
            raise

        if not self.config.custom_flow.flow.stop_after_end:
            self.set_next_run(task="CustomFlow", success=True, finish=False)
        raise TaskEnd
