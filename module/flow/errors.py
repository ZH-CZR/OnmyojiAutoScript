# -*- coding: utf-8 -*-
"""flow 相关的异常。"""


class FlowSchemaError(ValueError):
    """flow.json 结构不合法（缺字段、类型错、未知 op 等）。"""


class FlowAbort(Exception):
    """流程中某一步失败，需要终止整个流程。"""


class FlowEnd(Exception):
    """流程执行到 end 步骤，正常结束。

    :param success: 是否把这次运行标记为成功
    """

    def __init__(self, success: bool = True) -> None:
        super().__init__("flow end")
        self.success = success
