# -*- coding: utf-8 -*-
"""流程编排（flow）包：把 annotator 标注出来的规则串成可执行、可生成代码的步骤流程。

模块分工：
- schema      op 规格表 + 校验/标准化 + 条件求值（前端渲染、运行、生成代码共用同一份定义）
- runtime     FlowRunner：解释执行 steps，产出逐步结果（单步测试与真实运行共用）
- host        TaskFlowHost（真实设备）/ PreviewFlowHost（单帧预览，不点真机）
- rules       读 tasks/<Task>/res/*.json，把规则名解析成 RuleImage/RuleOcr/...
- store       flows/<name>.json 的读写
- codegen     把 flow 生成 tasks/<Task>/script_task.py
"""
from module.flow.errors import FlowAbort, FlowEnd, FlowSchemaError
from module.flow.runtime import FlowRunner, StepResult

__all__ = [
    "FlowAbort",
    "FlowEnd",
    "FlowSchemaError",
    "FlowRunner",
    "StepResult",
]
