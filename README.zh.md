<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> 注意：本译文仅供参考。[英文版 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) 为官方权威版本。PennyTune 的界面、命令和输出仅提供英文。如有任何不一致之处，以英文版为准。

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | 中文 | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

# PennyTune

**屏蔽噪音。**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune 是一款免费、开源、无需 API 密钥的取证式尽职调查工具，专为美国上市的微型股（micro-cap）而设计。**
将它对准你已持有或正在关注的股票代码，它便会从每家公司的 SEC 申报文件中呈现
风险信号和取证式警示标志——
会计质量与财务困境评分、稀释与公司行动风险、
内部人交易活动、8-K 重大事件、退市通知与正在进行的
交易暂停风险，以及交割失败（fails-to-deliver）结算背景——**全部
根据每家公司公开的 SEC 申报文件计算得出**，便于你自行评估该公司。

它完全运行在**公开、无需账户、无需 API 密钥的数据**之上：SEC EDGAR 是
唯一的数据源（上市公司全集、所有申报文件，以及
交割失败 / 交易暂停数据源）。**任何环节都不提供
自带密钥（bring-your-own-key）的选项**。

> PennyTune 呈现的是**供你自行尽职调查的证据**——它不会告诉
> 你某只股票是"干净的"还是"地雷"，不会给出买入/卖出建议，
> 也不会预测结果。它分析的是**在 SEC 注册的美国上市
> 公司**，并且**不获取任何实时价格**：它不会按当前
> 价格进行筛选，不会计算技术指标，也不会评估可交易性（买卖
> 价差 / 流动性）。你需提供待排名的股票代码，并自行在
> 券商处核实当前价格和可交易性。

---

## ⚠️ 免责声明——请仔细阅读

PennyTune 仅为一款研究和教育工具，并非投资建议。它不会告诉你应当买入、卖出或持有任何证券。微型股和细价股（penny stocks）具有极高风险，可能导致你的资金全部损失。完整免责声明为权威版本，其英文文本载于[英文版 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md)，亦可通过 `pennytune disclaimer` 命令查看。

---

## 它是什么

美国微型股板块中充斥着*事出有因*而显得便宜的公司——
现金消耗、不断稀释、濒临退市，或为操纵而设计。尽职
调查最困难的部分，就是阅读申报文件以找出这些地雷。PennyTune
替你完成这项阅读工作：将它对准一个股票代码，或对你
选定的一组精选股票代码进行排名，它便会从公司的 SEC 申报
文件中提取风险信号和取证式警示标志——**全部根据公司
公开的 SEC 申报文件计算得出**。

它呈现的是**证据，而非定论。**它不会告诉你某只股票是干净的
还是地雷，不会建议买入或卖出，也不会预测结果——
判断权在你手中。

- **免费且无需 API 密钥**——完全运行在无需账户、无需密钥的公开数据之上。
- **在 SEC 注册、于美国主要交易所（NYSE/NASDAQ/NYSE American）上市，绝不涉及场外市场（OTC）**——这是其内在设定。
- **基于证据**——每个信号都根据公司公开的 SEC 申报
  文件计算得出，对于事件驱动的红旗信号，还会指明具体的 8-K 条目。
- **透明且可调**——一个可分解的综合评分，配有用户可编辑的
  权重、筛选预设（`penny` 默认 / `micro` / `small-cap-value` /
  `broad` / `custom`），以及可选的策略配置档（`hold` 默认 /
  `trader` / `high-return` / `custom`）。
- **无实时价格**——它不获取当前价格，也不评估可交易性；
  请自行在券商处核实。
- **仅供研究，并非投资建议。**

## 它呈现什么

对于每家公司，PennyTune 都会阅读 SEC 申报文件，并对那些
对微型股最为重要的信号进行评级——每一项都根据公司的申报文件计算得出：

- **财务健康与困境**——Altman Z″ 偿付能力评分，外加一套
  取证式工具组（Beneish 盈余操纵模型与 Piotroski 强度模型），
  覆盖公司已申报的财务数据。
- **稀释与公司行动**——储架发行（shelf）和按市价发行（ATM，"at-the-market"），
  股数上升与稀释速度、连续反向拆股，以及
  从 8-K 记录中提取的审计师变更 / 重述（restatement）警示。
- **内部人交易活动**——公开市场上的内部人*买入*（信心信号），
  与例行授予和代扣税卖出严格区分开来，因此股权奖励绝不会被
  读作看涨——另有 Form 144 拟售出存量（overhang）以及 13D/13G 持股活动。
- **8-K 重大事件**——结构化的条目代码记录（重述、审计师
  变更、高管离职、上市资格不足及其他重大事项），
  按严重程度而非原始计数加权。
- **退市通知风险**——已披露的持续上市资格不足通知
  （8-K Item 3.01），如实报告，不会去猜测工具
  无法计算的价格时钟天数。
- **正在进行的交易暂停**——处于*当前* SEC 交易暂停
  状态的公司会被标记并予以排除；已过期的历史暂停会作为
  背景信息显示，不会据此对该公司不利。
- **交割失败**——来自 SEC 每月两次的交割失败数据所提供的
  结算压力背景（仅供参考——其本身并非操纵的证据）。
- **行业分类**——每家公司的 SIC 行业，因此质量和
  估值比较是在同行业、同规模的可比公司之间进行，而非依据
  绝对的临界值。

## 数据与署名

PennyTune 仅使用来自单一来源的公开、无需密钥的数据：**SEC EDGAR**（全集——
取自 SEC 的 `company_tickers_exchange.json` 上市公司文件——以及
所有申报文件、基本面数据、内部人表格，以及交割失败 /
交易暂停文件）。任何环节唯一需要的身份标识就是 SEC EDGAR 的
`User-Agent` 字符串（你的姓名 + 电子邮箱）——这是 SEC 公平访问
政策要求用于标识请求者的请求头，而非 PennyTune 账户、登录或
密钥。它仅存储在你的本地配置中（在 `config get` 中会被脱敏处理），仅
在 SEC 请求头中发送，绝不会传输给作者或任何第三
方。任何有效的个人电子邮箱均可使用；设置时只检查格式，而不检查提供商。

PennyTune 是一款研究工具，**不会**重新发布原始的第三方
数据集；你的配置和任何导出的结果都保留在本地（绝不提交）。

## 安装

PennyTune 是一款发布在 PyPI 上的命令行工具。用 pip 安装它——这是
简单、通用的默认方式：

```bash
pip install pennytune
```

由于它是一款 CLI，**隔离安装（推荐用于命令行工具）**
可以使其不干扰你其他的 Python 环境：

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

需要 Python 3.11-3.14（全部经过 Linux、macOS 和 Windows 的 CI 测试；3.13
是代码检查（linting）和类型检查的主要目标版本）。

**从源码安装（用于开发）：**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## 用法

首次设置会记录 SEC EDGAR 身份标识（一个必需的请求头——并非
密钥）以及风险确认；在两者都存在之前，`scan`/`inspect` 将拒绝运行：

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

主要工作流程是 **`inspect <TICKER>`**——将工具对准一家你
已持有的公司，获取根据其申报文件计算得出的完整取证式分解：

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` 会对**你选定的一组精选股票代码**进行排名——可显式给出，或从
你的关注列表中读取——依据是它们的 SEC 申报文件风险信号（不做价格筛选——该
工具不获取任何价格）。每次运行最多 100 个股票代码；PennyTune 绝不会扫描
整个市场。由于正向的质量子评分是同行业/同规模相对的
百分位（只有在大规模横截面上才有意义），在一个小型精选
集合上，排名主要由**风险/惩罚**信号（稀释、
困境、退市、内部人卖出）所驱动——它呈现的是你集合中风险最高的
股票。用 `--preset` / `--profile` 调节风险权重和策略：

```bash
pennytune scan AAA BBB CCC                       # rank the tickers you name
pennytune scan                                   # rank your watchlist (top 10)
pennytune --profile high-return scan AAA BBB --preset broad  # preset + profile
pennytune scan AAA BBB --exclude-serial-splitter --require-insider-buying

# Export the full ranked set (CSV/Parquet/JSON/Markdown); pipe clean JSON:
pennytune scan AAA BBB --format parquet
pennytune --json scan AAA BBB | jq '.results[0]'

# Offline / no-network run (degraded; no live SEC fetch):
pennytune --offline scan AAA BBB
```

其他所有命令：

```bash
pennytune --help              # all commands and global flags
pennytune --version           # app version + pinned dependency versions
pennytune disclaimer          # print the full legal disclaimer
pennytune watch add GROW NUKK # persistent watchlist (add | list | rm)
pennytune watch list          #   run-over-run score deltas + alerts
pennytune config get          # view all settings (EDGAR email redacted)
pennytune config set weights.valuation 1.5   # tune a scoring weight
pennytune config set profile custom          # switch to hand-tuned weights
pennytune sources             # data sources, free-tier limits, contacted domains
```

输出以一个数据新鲜度标头开始（当前生效的预设/配置档 + 各域的截至
时间戳），在相关时显示关注列表提醒横幅，对前 N 名进行排名，并以
简短的免责声明结尾。导出的文件带有单行的免责声明标头，
因此免责声明会随数据一同传递。

## 开发

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

依赖项在已提交的 `uv.lock` 中以哈希方式锁定（供应链纪律）。
升级都是经过审慎考量并经审查的；不会有任何内容自动合并。

## 许可证

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)。© Lavelle Hatcher Jr.

---

## ⚠️ 免责声明（重复）

PennyTune 仅为一款研究和教育工具，并非投资建议。它不会告诉你应当买入、卖出或持有任何证券。微型股和细价股（penny stocks）具有极高风险，可能导致你的资金全部损失。完整免责声明为权威版本，其英文文本载于[英文版 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md)，亦可通过 `pennytune disclaimer` 命令查看。
