# 上游来源记录

`manifest.json` 由 `dev_tools/upstream_sync.py` 生成。记录固定的第一仓库基底、第二仓库参考提交，以及受管理文件的原始和安装 SHA-256；适配后的内容与原始哈希不同属于正常情况。

`project_url` 与 `project_branch` 记录本项目发布来源 `https://gitee.com/oYe486/onmyoji-auto-script.git` / `master`。两个参考源码仓库的地址保留用于溯源，不作为普通安装的更新来源。

`upstream_sha256: null` 表示第一仓库回退文件或本地生成的页面列表，不是第二仓库原样文件。不要用这些记录表示已经完成游戏实测。

源码选择、闭源隔离、更新和验证流程见 [重构维护说明](../docs/REFACTOR.md)。
