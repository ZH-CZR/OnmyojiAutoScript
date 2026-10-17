# GUI 资源

`gui.py` 的本地 Qt 界面直接加载 `module/gui/qml/app.qml`。QML 源文件保留以支持编辑，`qml.qrc` 是资源目录清单；旧的未使用生成文件 qml_rc.py、qml_rcc.py 已移除。

图片资源仍由 `res_rcc.py` 提供。修改图片后，在已有 PySide6 环境从本目录执行 `pyside6-rcc -o res_rcc.py res.qrc` 重新生成。

`module/gui/FluentUI/` 是实际运行需要的插件，继续保留。仓库根目录原 fluentui/ 是插件构建源码、示例与文档，已备份移出，不影响现有插件加载。许可证保存在 `docs/licenses/FluentUI.txt`。
