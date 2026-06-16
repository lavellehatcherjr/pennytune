<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> 注意: これは情報提供のみを目的として提供される翻訳です。公式かつ正式な版は[英語版 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md)です。PennyTune のインターフェース、コマンド、および出力は英語でのみ利用可能です。万一齟齬がある場合は、英語版が優先されます。

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | 日本語 | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

# PennyTune

**ノイズをチューンアウトしよう。**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune は、米国上場のマイクロキャップ（超小型株）を対象とした、無料・オープンソース・API キー不要のフォレンジック・デューデリジェンスツールです。**
すでに保有している、または注視しているティッカーを指定すると、各企業の SEC 提出書類に含まれるリスクシグナルやフォレンジックなフラグを抽出します。
具体的には、会計品質スコアと財務ディストレス（経営難）スコア、希薄化リスクおよびコーポレートアクションリスク、
インサイダー（内部者）活動、8-K の重要事象、上場廃止通知リスクおよび現行の取引停止リスク、
そしてフェイル・トゥ・デリバー（受渡不履行）に関する決済状況などであり、これらはすべて **各企業の公開された SEC 提出書類から算出** されるため、企業をご自身で評価できます。

本ツールは、完全に **公開・アカウント不要・API キー不要のデータ** のみで動作します。SEC EDGAR が
唯一のデータソースです（上場企業ユニバース、すべての提出書類、および
フェイル・トゥ・デリバー／取引停止のフィード）。**独自キーを持ち込むオプションは
どこにも存在しません**。

> PennyTune は **ご自身のデューデリジェンスのための材料（エビデンス）** を提示するものです。ある銘柄が
> 「クリーン」なのか「地雷」なのかを判断するものではなく、売買のアドバイスを行うものでもなく、
> 結果を予測するものでもありません。本ツールは **SEC に登録された米国上場企業** を分析対象とし、
> **ライブ価格は一切取得しません**。現在価格によるスクリーニング、テクニカル指標の算出、
> 取引可能性（ビッド・アスク・スプレッド／流動性）の評価のいずれも行いません。ランク付けするティッカーはご自身で指定し、
> 現在価格と取引可能性はご自身で証券会社にて確認してください。

---

## ⚠️ 免責事項 - 必ず注意してお読みください

PennyTune は調査および教育目的のツールであり、投資助言ではありません。本ツールは、いかなる証券についても、買うべきか、売るべきか、保有すべきかを指示するものではありません。マイクロキャップ株およびペニー株は、投資元本の全額損失を含む、極めて高いリスクを伴います。正式版である完全な免責事項は、英語版で[英語版 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) に掲載されているほか、`pennytune disclaimer` コマンドでも確認できます。

---

## 概要

米国のマイクロキャップ領域には、*それ相応の理由があって* 割安に見える企業が
あふれています。現金を燃やし続けている、希薄化している、上場廃止が間近、
あるいは相場操縦向けに仕組まれている、といった企業です。デューデリジェンスの
難しい部分は、こうした地雷を見つけ出すために提出書類を読み込むことにあります。PennyTune は
その読み込みをあなたの代わりに行います。ティッカーを 1 つ指定するか、あなたが選んだ
キュレーション済みのティッカー群をランク付けすると、企業の SEC 提出書類から
リスクシグナルとフォレンジックなフラグを抽出します。これらは **企業の公開された SEC
提出書類から算出** されます。

本ツールが提示するのは **判定（評決）ではなく、材料（エビデンス）** です。ある銘柄がクリーンなのか
地雷なのかを判断することはなく、売買を助言することもなく、結果を予測することもありません。
判断はあなた自身が行います。

- **無料・API キー不要** - 完全にアカウント不要・キー不要の公開データのみで動作します。
- **SEC 登録済みで、米国の主要取引所（NYSE／NASDAQ／NYSE American）に上場、OTC は対象外** - 設計上そうなっています。
- **エビデンスベース** - すべてのシグナルは企業の公開された SEC
  提出書類から算出され、イベント起因のレッドフラグについては該当する具体的な 8-K の項目が明示されます。
- **透明性が高く、調整可能** - 分解可能なコンポジットスコアにユーザー編集可能な
  ウェイトを備え、スクリーニングのプリセット（`penny`（デフォルト）／`micro`／`small-cap-value`／
  `broad`／`custom`）、および選択可能な戦略プロファイル（`hold`（デフォルト）／
  `trader`／`high-return`／`custom`）を提供します。
- **ライブ価格なし** - 現在価格の取得や取引可能性の評価は行いません。
  それらはご自身で証券会社にて確認してください。
- **調査目的のみであり、投資助言ではありません。**

## 何を提示するか

PennyTune は各企業について SEC 提出書類を読み込み、マイクロキャップにとって
最も重要なシグナルを評価します。いずれも企業の提出書類から算出されます。

- **財務の健全性とディストレス（経営難）** - Altman Z″ による支払能力スコアリングに加え、
  フォレンジックな分析一式（Beneish の利益操作モデルと Piotroski の財務強度モデル）を、
  企業が提出した財務情報に対して適用します。
- **希薄化とコーポレートアクション** - シェルフ登録および ATM（「アット・ザ・マーケット」）増資、
  発行株式数の増加と希薄化のスピード、繰り返される株式併合（シリアル・リバース・スプリット）、
  および 8-K の記録から得られる監査人交代／訂正報告のフラグ。
- **インサイダー（内部者）活動** - オープンマーケットでのインサイダーによる *買い*（確信度のシグナル）。
  これは通常の付与（グラント）や税金の源泉徴収のための取引とは明確に区別され、付与が
  強気のシグナルとして読み取られないようにしています。さらに、Form 144 による売却予定のオーバーハングや 13D/13G の保有活動も含みます。
- **8-K の重要事象** - 構造化された項目コードのテープ（訂正報告、監査人
  交代、役員の退任、上場基準不適合およびその他の重要事項）を、単純な件数ではなく
  重大性で重み付けします。
- **上場廃止通知リスク** - 開示された継続上場基準の不適合通知
  （8-K の Item 3.01）を、本ツールが算出できない価格基準の残日数（プライスクロック）を
  推測することなく報告します。
- **現行の取引停止** - *現在* SEC による取引停止下にある企業はフラグ付けされ、
  除外されます。失効した過去の取引停止は、企業の不利に扱うのではなく、
  状況（コンテキスト）として表示されます。
- **フェイル・トゥ・デリバー（受渡不履行）** - SEC の隔月のフェイル・トゥ・デリバー
  データから得られる決済ストレスの状況（あくまで状況であり、それ自体が相場操縦の証拠ではありません）。
- **セクター分類** - 各企業の SIC セクター。これにより、品質とバリュエーションの比較が、
  絶対的な閾値ではなく、同セクター・同規模のピア（同業他社）に対して
  行われます。

## データと帰属（アトリビューション）

PennyTune は、単一のソースである **SEC EDGAR** から取得した、公開・キー不要のデータのみを
使用します（ユニバースは SEC の `company_tickers_exchange.json` 上場企業ファイルから取得し、
すべての提出書類、ファンダメンタルズ、インサイダーフォーム、およびフェイル・トゥ・デリバー／
取引停止ファイルも同様です）。本ツールのいずれの箇所においても必要となる唯一の本人情報は、SEC EDGAR の
`User-Agent` 文字列（あなたの氏名＋メールアドレス）です。これは、リクエスト元を識別するために SEC の
フェアアクセスポリシーが要求するリクエストヘッダーであり、PennyTune のアカウント、ログイン、または
キーではありません。これはあなたのローカル設定にのみ保存され（`config get` ではマスク表示されます）、SEC への
リクエストヘッダーでのみ送信され、著作者やいかなる第三者にも一切送信されません。
有効な個人用メールアドレスであれば何でも機能します。セットアップでは形式を確認するのみで、プロバイダーは確認しません。

PennyTune は調査ツールであり、第三者の生データセットを再公開することは **ありません**。
あなたの設定およびエクスポートされた結果はローカルに留まります（コミットされることはありません）。

## インストール

PennyTune は PyPI で公開されているコマンドラインツールです。シンプルで普遍的な
デフォルトである pip でインストールします。

```bash
pip install pennytune
```

CLI であるため、**隔離されたインストール（コマンドラインツールに推奨）** を用いると、
他の Python 環境を汚さずに済みます。

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Python 3.11〜3.14 が必要です（すべて Linux、macOS、Windows で CI テスト済み。3.13
がリンティングおよび型チェックの主要なターゲットです）。

**ソースから（開発用）:**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## 使い方

初回セットアップでは、SEC EDGAR の本人情報（キーではなく、必須のリクエスト
ヘッダー）とリスクの承認を記録します。`scan`／`inspect` は両方が
そろうまで実行を拒否します。

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

主なワークフローは **`inspect <TICKER>`** です。すでに保有している企業に
本ツールを向けて、提出書類から算出された完全なフォレンジック内訳を取得します。

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` は、**あなたが選んだキュレーション済みのティッカー群** を、SEC 提出書類の
リスクシグナルに基づいてランク付けします（明示的に指定するか、ウォッチリストから
読み込みます。価格フィルタリングは行いません。本ツールは価格を一切取得しません）。1 回の実行あたり最大 100 ティッカーで、PennyTune が
市場全体をスキャンすることは決してありません。ポジティブな品質サブスコアは
セクター／規模相対のパーセンタイル（大規模な横断データ全体でのみ意味を持ちます）であるため、
小規模なキュレーション済みの集合では、ランキングは主に **リスク／ペナルティ** のシグナル
（希薄化、ディストレス、上場廃止、インサイダー売り）によって決まり、あなたの
集合の中で最もリスクの高い銘柄を浮かび上がらせます。リスクの重み付けと戦略は `--preset` / `--profile` で調整します。

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

その他のすべてのコマンド:

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

出力はまず鮮度（フレッシュネス）ヘッダー（有効なプリセット／プロファイル＋ドメインごとの
as-of スタンプ）から始まり、該当する場合はウォッチリストのアラートバナーを表示し、上位 N 件を
ランク付けし、最後に短い免責事項を付けて終わります。エクスポートされたファイルには 1 行の免責事項ヘッダーが
付与されるため、免責事項がデータとともに移動します。

## 開発

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

依存関係は、コミットされた `uv.lock` でハッシュ固定（ピン留め）されています（サプライチェーンの規律）。
アップグレードは意図的に行われ、レビューされます。自動マージされるものは何もありません。

## ライセンス

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ 免責事項（再掲）

PennyTune は調査および教育目的のツールであり、投資助言ではありません。本ツールは、いかなる証券についても、買うべきか、売るべきか、保有すべきかを指示するものではありません。マイクロキャップ株およびペニー株は、投資元本の全額損失を含む、極めて高いリスクを伴います。正式版である完全な免責事項は、英語版で[英語版 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) に掲載されているほか、`pennytune disclaimer` コマンドでも確認できます。
