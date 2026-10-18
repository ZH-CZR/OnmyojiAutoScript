# 探索章节识别

2026-10-17 修复探索进入大世界后选择章节时的 OCR 接口不兼容。
日志中的 `AttributeError: 'RuleOcr' object has no attribute 'preprocess_ocr_image'`
来自 `tasks/Exploration/base.py` 的 `_detect_visible_chapters()`。

章节识别直接把完整截图交给 `RuleOcr.detect_and_ocr()`，由其按 ROI 裁剪、
调用 `pre_process()` 并过滤低置信度结果，不额外裁剪或引入新的图像增强。

公共 `BoxedResult` 只有 `box`、`text_img`、`ocr_text` 和 `score`，没有
`after_box`。选中章节时取 `box` 四点的最小、最大坐标构成矩形，加上章节
OCR 的 ROI 左上角偏移，转换为 `RuleClick` 所需的屏幕 `(x, y, width, height)`。
每次重新截图都清空上一次目标位置，避免重试时点击过期的识别位置。

离线验证：

```powershell
.venv\Scripts\python.exe -m unittest dev_tools.test_exploration_chapters dev_tools.test_task_startup dev_tools.test_server_startup -q
```

章节回归使用真实 `RuleOcr` 和 `BoxedResult`，模拟底层 OCR 返回值，覆盖
裁剪区域、低置信度过滤、空结果，以及目标章节从识别到屏幕点击位置的流程。
不连接模拟器或启动 OCR 服务；离线通过不代表真实 OCR、设备或游戏流程已实测。
