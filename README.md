# 私人账本

本地运行的单用户记账 Web App：Flask 后端、SQLite 持久化、无第三方前端资源。只使用本人提供的文件；`examples/demo.csv` 是从零编写的完全虚构数据，不是脱敏账单。

## Mac 首次使用

在 GitHub 点击 **Code → Download ZIP**，双击解压，文件夹一般叫 `finance-main`。打开终端，输入 `cd `（后面有一个空格），把该文件夹从 Finder 拖进终端，按回车；不需要手动猜下载路径。

已经安装 Python 3.12 后，逐行执行：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python app.py init
.venv/bin/python app.py serve --host 127.0.0.1 --port 8000
```

密码至少 12 字符，输入时不会显示。保持终端开着，在这台 Mac 的浏览器打开 `http://127.0.0.1:8000`。停止按 Control+C。以后进入同一个文件夹，只执行最后一条启动命令；不要重新初始化密码或删除 `.runtime`。账目不会上传到 GitHub。

## 启动

要求 Python 3.12（当前环境已安装依赖）。在你自己的电脑或服务器：

```bash
cd /workspace/finance
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python app.py init
.venv/bin/python app.py serve --host 127.0.0.1 --port 8000
```

`init` 通过终端隐藏输入设置至少 12 字符的密码，没有默认密码。它保留账本并撤销现有会话。打开本机 8000 端口登录后，先创建独立账户，再导入文件。路径 `/workspace/finance` 是当前项目目录，搬到自己的机器时替换为实际目录。不要把密码写进命令参数、源码或聊天。停止服务用 Ctrl+C。

默认数据目录 `.runtime/`（权限 0700），文件权限 0600。可设置 `LEDGER_DATA_DIR` 为你自己的私人目录，必须同时保留数据库、session.key、password.hash 和 files。不要指向 public、static、assets 或反向代理静态目录。账户不自动合并：debit、chequing、savings、每张信用卡分别建账。不同本币分开筛选，绝不猜汇率。

云环境安装脚本运行 `scripts/bootstrap.py`，仅在空实例创建随机初始密码并放在私人 `.runtime/initial-password.txt`，不会输出到日志、不会导入样例、不会覆盖已有密码。可在自己的终端查看该文件；建议首次实际使用前运行 `app.py init` 设置自己的密码，此操作会删除初始密码文件。云环境不提供 localhost 预览链接。

## 已实现

- 月度／年度切换；默认最新有记录月份；交易日期按自然月归属，银行入账日期单独保存。
- 收入、消费、收入减消费；退款、分摊收款、取现、转账、还款和 pending 分开显示与查询。房贷／车贷仅记录明确的实际扣款，不拆本金利息。
- 稳定分类颜色；饼图扇区与完整金额排序列表；大类、二级分类、原始交易下钻；搜索和排序；手机抽屉式滚动详情、键盘操作。
- 单笔修改类型／分类／备注；明确勾选才创建未来完全相同描述规则，不追溯改动其他记录；已有手工修改始终保留。
- 本地 CSV、XLSX、标准文本 PDF 解析；先预览再确认；来源文件下载、页码／行号；重复文件和重叠交易去重，临时记录更新保持 ID。
- 资料覆盖按文件明确声明；缺口按账户逐日计算。观察到的交易起止日期不是完整覆盖。年度标题截至最新导入交易，未导入月份标记缺失。
- Excel 按年一个 sheet、各账户连续分区，保留稳定 ID 和来源。收入／消费／结余／分类占比为直接引用交易的 SUMIFS 等公式；每次导出来自当前 SQLite 同一份数据。

## 导入格式

CSV：UTF-8，可含 BOM。Excel：`.xlsx`、一个 sheet、首行为列名；金额和日期不能是公式。旧 `.xls` 先在本机另存 `.xlsx`。以下列名大小写固定：

| 列 | 规则 |
|---|---|
| transaction_date | 必填真实交易日期，`YYYY-MM-DD`，无完整年份就拒绝，不用入账日期补猜 |
| posting_date | 银行入账日期，允许空值，表头仍需存在 |
| description | 原始商户／银行描述；不推断用途 |
| amount | 账单本币正数，最多两位小数，不带 `$` 或千分位逗号 |
| currency | 与账户本币相同，如 CAD；表头须存在，空值采用已明确设置的账户币种 |
| type | 明确填写下表之一；不能直接根据金额正负或商户推测 |
| status | `posted` 或 `pending`；空值表示明确导入已入账记录 |
| external_id | 银行提供的稳定交易 ID（可选；不是账单行号） |
| original_amount / original_currency | 同时提供或同时留空，保留原币；不重算本币汇率 |
| category / subcategory | 可选，缺省「待确认」；须为已经创建的分类组合 |
| notes | 可选备注 |

| type | 财务口径 |
|---|---|
| income | 工资、利息等明确收入 |
| expense | 已发生消费、明确房贷／车贷扣款 |
| transfer | 自己账户间／投资资金转移，不是收入或消费 |
| payment | 信用卡还款，不重复计算消费 |
| refund | 退款／返现单列，不算收入、不冲减消费 |
| reimbursement | 分摊／归还借款单列，不算工资 |
| withdrawal | 取现单列，随后现金消费单独录入，避免重复计入消费 |

银行的借贷金额正负惯例不同，**请本人先映射和核对 type**。有无法确定的收支类型时暂停该行，不猜测。已明确是消费但不知道用途的记录归「待确认」。预览可调整分类和类型、跳过行；日期和金额有问题则修正本地结构化文件重传。整笔导入有错误则回滚，历史保留。

文件最大 20MB、20,000 笔。预览临时文件在私人 staging 保存最多一小时，之后下次上传时清理。覆盖范围不从交易推算：只有确知文件包含某账户范围内完整资料时填写开始与结束。可以留空，页面会标记未知。

### PDF 与 Monopoly

内置 PDF 规则只接受含文本层、每页有标准 `|` 分隔表头和完整单行数据的 PDF（和 CSV 列名相同）。页码、文本行号保留。未知银行版式、扫描件、断行、加密文件明确失败，不尝试外部 AI/OCR。通用解析不意味着支持所有银行。

已读取 [Monopoly 官方 README](https://github.com/benjamin-awd/monopoly)，在隔离虚拟环境尝试 `monopoly-core==0.23.2`。修正编译器设置后仍缺少 `poppler/cpp/poppler-document.h`；本版本未接入 Monopoly。官方要求 Poppler 开发依赖等系统组件，因此不会假装转换已验证。若以后使用本人提供的银行 PDF，先在本机安装官方依赖，并仅启用本地预定义银行解析；不要使用 `--llm`、Gemini 或在线示例。转换后映射标准 CSV，并人工检查日期、金额、借贷方向、换行和余额。转换命令成功不代表账目准确。

平台没有 PDF／Spreadsheets skill；本项目使用 pypdf／openpyxl，已用自己生成的虚构 PDF 和 Excel 实测。没有安装 Actual Budget，不维护第二套账本。

### 去重边界

同一账户重复文件 SHA-256 直接拦截。银行 ID 优先，同 ID 日期／金额变化须确认。缺少银行 ID 时使用交易日期、原始描述、本币金额和出现次数精确匹配，同文件两笔同额消费保留两笔。

没有 ID 时，两个不同来源里恰好同日同描述同金额的独立消费与重叠账单记录无法可靠区分；预览明确提示。核对原件，必要时提供本人确认的不同 external_id。不得用模糊商户匹配自动合并。临时记录日期／描述变化时，预览列出同账户、同本币、同金额的 pending 候选，必须本人选择或确认是新记录；金额也变化且没有稳定银行 ID 时，本版本不自动匹配，先本人核对后补稳定 ID，不可盲目重复入账。更新保留 ID、手工分类、类型、备注，并追加来源。跳过行仍保留文件导入记录，若需要补录，请生成核对后的新文件。

## 私人部署、备份

默认只监听 loopback。远程使用必须放在**你自己的 HTTPS 反向代理**后，例如 Nginx，将全部请求代理给 Flask，绝不把数据目录映射为静态资源。设置 `LEDGER_HTTPS=1` 启用 Secure cookie/HSTS；通过 HTTPS 访问后登录。不要直接公开 HTTP 8000 端口。非本地 HTTPS 部署没有在本任务创建或发布，需要你的域名和服务器；没有开通任何付费服务。

```bash
export LEDGER_DATA_DIR=/your/private/ledger-data
export LEDGER_HTTPS=1
.venv/bin/python app.py init
.venv/bin/python app.py serve --host 127.0.0.1 --port 8000
```

单用户实例，无公开注册和多租户功能。所有账本页面、交易 API、导入、导出和原件下载都在服务端检查有期限且可撤销的会话；写操作还验证 CSRF。Cookie 为 HttpOnly、SameSite=Strict。日志不输出账单、密码或完整异常局部变量。密码使用 scrypt 哈希，仅在服务器保存。会话密钥不进入前端。

备份：停止你启动的服务后，完整复制私人数据目录到你自己加密的存储（包括数据库和 files）；恢复先停止服务，放回完整目录再启动。不要运行中的裸复制 SQLite WAL 文件组合。导出 Excel **不是完整备份**。浏览器下载的文件也属于私人数据，应放在自己的私人目录。

`.gitignore` 排除数据、账单、数据库、导出、截图、日志、环境文件和凭证；本仓库开始时没有跟踪文件，也没有读取 Git 历史。发布代码前运行 `python scripts/check_release.py`；只允许代码、文档、依赖锁定和虚构 CSV 样例。检查新增的前端资源不含真实数据或第三方请求。不要在该目录外随意新建真实 CSV 然后提交。**云环境 Publish 会保存文件系统快照，真实资料不要放进共享的开发环境；只在本人私人部署实例导入。**

## 验证

```bash
.venv/bin/python -m pytest -q
node --check assets/app.js
.venv/bin/python scripts/check_release.py
```

测试实际执行 CSV、XLSX、虚构 PDF 解析、重复和重叠导入、银行 ID、跨年跨月、pending 更新及来源、手工规则保留、所有财务类型、整数分、层级合计、公式结构、Excel 文本注入保护、资料覆盖、重启持久化、未登录权限、CSRF 和退出后会话撤销。

浏览器功能验证使用环境已有 Chromium，并验证 1440／390／320px 布局、月份默认值、导入预览与确认、分类下钻、备注修改、年度标题和键盘图表。Excel 公式由 Excel／LibreOffice 打开后重算；服务器不声称验证过桌面 Excel 计算引擎。详见 [验证记录](docs/VALIDATION.md) 和 [数据结构](docs/DATA.md)。

设计已读取并使用 [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) 的指导及本地查询（财务仪表盘匹配），和 [Impeccable](https://github.com/pbakaus/impeccable) 的产品／设计文档及界面审查流程。营销、暗色或玻璃建议不符合用户明确的记账任务和配色，未采用；字体使用系统中文字体，不向外部字体服务发送请求。
