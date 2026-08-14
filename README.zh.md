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
- **在 SEC 注册的申报主体**——股票代码全集来自 SEC 的公开数据。这里没有交易所
  筛选：场外市场（OTC）报价的股票与其他股票一样被扫描，而所依据的那份 SEC
  文件本身也不含 NYSE American 这一标识。
- **基于证据**——凡是被计算出来的信号，都来自公司公开的 SEC 申报文件，对于事件
  驱动的红旗信号，还会指明具体的 8-K 条目。但有两个贡献项——估值与报道情绪——在
  本版本中没有数据源，始终被抑制（参见**局限**）。
- **透明且可调**——一个可分解的综合评分，配有用户可编辑的
  权重、筛选预设（`penny` 默认 / `micro` / `small-cap-value` /
  `broad` / `custom`），以及可选的策略配置档（`hold` 默认 /
  `trader` / `high-return` / `custom`）。
- **无实时价格**——它不获取当前价格，也不评估可交易性；
  请自行在券商处核实。
- **仅供研究，并非投资建议。**

## 它呈现什么

对于每家公司，PennyTune 都会阅读 SEC 申报文件，并对那些
对微型股最为重要的信号进行评级。凡是无法计算的信号都会被抑制并如实报告，
绝不会当作零分计入：

- **财务健康与困境**——Altman Z″ 偿付能力评分，外加一套
  取证式工具组（Beneish 盈余操纵模型与 Piotroski 强度模型），
  覆盖公司已申报的财务数据。
- **稀释与公司行动**——储架发行（shelf）和按市价发行（ATM，"at-the-market"），
  股数上升与稀释速度、连续反向拆股，以及
  从 8-K 记录中提取的审计师变更 / 重述（restatement）警示。
- **内部人交易活动**——公开市场上的内部人*买入*（信心信号），
  与例行授予和代扣税卖出严格区分开来，因此股权奖励绝不会被
  读作看涨——另有 Form 144 拟售出存量（overhang）以及 13D/13G 持股活动。
- **8-K 重大事件**——结构化的条目代码记录，按严重程度而非原始计数加权。
  Item 4.02，即发行人声明其自身此前公布的财务报表已不可依赖，会与
  Item 4.01（审计师变更）分开单独标明并计数；高管离职、上市资格不足
  及其他重大事项同样如此。
- **退市通知风险**——已披露的持续上市资格不足通知
  （8-K Item 3.01），如实报告，不会去猜测工具
  无法计算的价格时钟天数。
- **交易暂停**——在过去 180 天内被 SEC 暂停交易的公司会被标记并予以排除。请注意，
  本工具并不追踪该暂停此后是否已经失效：SEC 的交易暂停最长 10 个交易日，因此
  一只股票可能因为一次早已失效的暂停而被排除在外。
- **交割失败**——来自 SEC 每月两次发布的交割失败数据所提供的
  结算压力背景（仅供参考——其本身并非操纵的证据）。
- **SEC 问询函（comment letter）**——过去一年内 SEC 公司融资部（Division of
  Corporation Finance）是否与该公司有过往来函件、该窗口内有多少封问询函和
  多少份发行人回复，以及最近一封问询函的日期。仅供参考，绝不参与评分。
  申报索引只记录问询函本身，不记录其主题。
- **行业分类**——每家公司的 SIC 行业会被记录并显示。它只是背景信息：评分使用
  固定的参照区间，而非同业比较。

## 评分是如何计算的

综合评分是一个**未归一化的、按风险加权的研究评分**：

    综合 = Σ(权重 x 正向子评分) - Σ(惩罚 x 严重程度 x 置信度)

* **正向贡献项**依据**固定的参照区间**评级——Piotroski 的 0-9 量表、Altman Z″
  偿付能力区间，以及固定的 EV/营收与营收增长区间。因此一家公司的子评分只取决于
  它自己的申报文件，而与同一次运行中还有哪些其他股票无关，并且可以跨运行比较。
* **惩罚项**做减法，并按严重程度和当前生效的预设进行缩放。
* **分数越低，意味着从申报文件中发现的风险越多。** 它不是估值，不是预测，也无法与
  目标价相比。分数高只意味着"在申报文件中发现的风险较少"，绝不意味着"这只股票会涨"。
* 该评分**不设上下限**，也没有固定区间；请把它当作一种排序，而不是一个量值。

**对于完全没有获取到 SEC 证据的股票代码，不予评分。** 它会被报告为
`NOT ASSESSED`，在控制台中点名，并被排除在排名之外，这样证据的缺失就绝不会被
误认为风险的缺失。

**财务健康使用重新锚定的临界值，而非 Altman 公开发表的区间。** Altman Z″ 仍按其
公开发表的系数计算，但偿付能力临界值是 **-3.0 和 1.0**，而不是公开发表的 1.1 和
2.6，并且子评分是连续评级而非三档跳变。以 194 家真实申报公司为样本，用每家公司
自己年报中的持续经营（going concern）表述作为独立的困境标签测得：在公开发表的
临界值下，**41 家有持续经营表述的公司一家都没有漏掉，但 153 家健康公司中有 47 家
被判为困境**——其中包括 Starbucks、HP、AbbVie、Amgen、Oracle、Lowe's、Duke Energy
和 AT&T。公开发表的 1.1 这条界线位于真实分布的第 45 百分位。重新锚定后的临界值把
这一误判困境率从 31% 降到 12%，并且依然不会把任何有持续经营表述的公司判为安全。
这是对公开发表模型的一次有意偏离。

导出文件带有 `suppressed`、`suppressed_count`、`evidence_complete` 和
`completeness` 四列，因此无需阅读文字描述即可分辨一行是已评估还是未评估。

## 局限

在信任任何排名之前，请先读这一节。

* **有两个贡献项永远为零。** `valuation` 和 `sentiment` 在本版本中没有数据源——既
  没有市值数据源，也没有新闻数据源——因此对每一家公司、每一次运行都会被抑制。
* **对大约四分之一的大盘股，Altman 无法计算。** 银行和 REIT 不公布分类资产负债表，
  另有相当一部分大型申报主体不公布营业利润小计。凡是无法计算的，都会被抑制并如实
  报告，绝不做填补——但那只股票的财务健康贡献项也就整个缺失了。
* **大多数行都建立在不完整的证据之上。** 在一次具有代表性的 20 只股票扫描中，有
  18 只至少有一项检查无法执行。每一行缺了几项，由 `suppressed_count` 列给出。
* **本工具的排名是弱排名，不具权威性。** 它适合用来决定先读哪些申报文件。它不是
  一个可以直接据以行动的筛选器，任何单一标记都不应被当作定论。
* **问询函记录是历史，不是尚未了结的问题。** SEC 最早也要在审阅结束后 20 个工作日
  才会公开工作人员的问询函，而申报索引中并不含主题。本工具能告诉你曾经有过往来
  函件以及发生的时间；它无法告诉你问了什么，也无法告诉你是否还有事项悬而未决。
  一封问询函没有对应的回复申报，并不意味着无人回复——发行人常常在另一份申报文件
  之中作答。
* **被关注的股票在首次运行时绝不会触发提醒。** 提醒是与上一次快照相比得出的，
  因此一家公司在至少被扫描两次之前不会报出任何内容。
* **没有缓存。** 每次运行都会重新从 SEC EDGAR 获取数据。`config get` 显示的
  `cache_ttl` 设置不起任何作用。

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
整个市场。正向子评分依据**固定的参照区间**评级，因此一家公司的评分不取决于同一次
运行中还有哪些其他股票，并且可以跨运行比较。不过排名仍然主要由**风险/惩罚**信号
（稀释、困境、退市、内部人卖出）所驱动，因为申报文件对这些信号的支撑最充分。
用 `--preset` / `--profile` 调节权重和策略：

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
pennytune watch list          #   run-over-run score deltas
pennytune config get          # view all settings (EDGAR email redacted)
pennytune config set weights.valuation 1.5   # tune a scoring weight
pennytune config set profile custom          # switch to hand-tuned weights
pennytune sources             # data sources, rate limits, contacted domains
```

`scan` 的输出以一个标头开始（当前生效的预设/配置档 + 数据新鲜度各行），对前 N 名
进行排名，并以简短的免责声明结尾。导出的文件带有单行的免责声明标头，
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
