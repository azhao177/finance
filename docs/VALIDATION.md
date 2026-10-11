# 验证记录

验证全部使用自己编写的虚构记录及测试专用临时数据库，没有访问私人账单、数据库、账户、截图或 Git 历史。

- 后端：`python -m pytest -q`，31 项实际执行并全部通过，未跳过。包含 CSV/XLSX/虚构 PDF、重复文件、重叠交易及同文件出现次数、银行 ID、跨月跨年、pending 转正式保留 ID/手工分类/备注/来源、全部特殊类型、精确整数分、分类层级、公式及文本防注入、资料覆盖、重启、鉴权、CSRF、会话撤销、favicon 登录回归。新增表头别名、逗号／Tab／分号、明确日期格式、未知类型拦截、仅返回表头、XLSX 映射、映射与标准文件重叠去重；更新程序验证保留虚构私人文件及虚拟环境，拒绝非法路径和非代码文件。
- 浏览器：环境已有 `/usr/bin/chromium`，用 Playwright 在隔离虚构实例完成导入预览及提交、最新月份选择、月度数字、二级下钻、备注编辑、年度最新导入日期、缺失月份、图表键盘操作，以及 Tab／别名导入、列映射、明确日期选择、未知类型拦截后人工确认。1440／390／320px 无横向溢出；窄屏金额不截断；对滚动弹窗用可见窗口截图验证。无 JavaScript 错误。
- 图表：本月虚构消费 1,546.43 CAD，列表与二级明细一致；不足 3% 的车分类保留扇区、不绘制文字。年度学习类实际不足 3%（虽列表四舍五入为 3.0%），图上正确隐藏标签；以未四舍五入比例判定。
- 界面：使用 Impeccable 独立完成审查，最终 disposition 为 `ship`；范围是提供的五份有效虚构截图与界面源码，未声称独立审计后端鉴权。首次弹窗整页采集异常已改为窗口采集；320px 金额和弹窗初始滚动位置已修正。
- 发布内容：检查当前已跟踪及未忽略候选路径、前端外部请求／源码映射、拟交付代码／文档／虚构样例；真实文件／SQLite／凭证／截图／日志不在版本控制候选中。经本人授权将代码和虚构样例提交并推送至其 GitHub 仓库，未发布真实账目或生产服务。
- 环境：锁定依赖重装命令及 bootstrap 均实际执行；重复 bootstrap 不覆盖密码或数据。正式实例是空账本，启动 Waitress 后用本地请求实际登录并读取鉴权 API 验证；虚构演示测试独立。

复现：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_browser.py --chromium /usr/bin/chromium
.venv/bin/python scripts/check_release.py
```

可用 `--screenshots /tmp/fictional-ledger-review` 保留虚构浏览器截图。浏览器验证不会读写正式 `.runtime`。

明确未验证：任意银行 PDF 的专有版式、真实资料核对、OCR、Excel／LibreOffice 实际公式计算引擎、远程 HTTPS 部署和新云任务快照恢复。Monopoly 的安装缺 Poppler 开发依赖，未宣称可用；本地标准 PDF 已验证。当前应用为单用户实例，不能共享成多租户。UI UX Pro Max 与 Impeccable 指导已读；平台 PDF／Spreadsheets skill 未提供。
