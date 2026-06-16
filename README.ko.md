<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> 참고: 이 문서는 정보 제공 목적으로만 제공되는 번역본입니다. [영문 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md)가 공식적이고 권위 있는 버전입니다. PennyTune의 인터페이스, 명령어, 출력은 영어로만 제공됩니다. 내용에 불일치가 있는 경우 영문 버전이 우선합니다.

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | 한국어 | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

# PennyTune

**소음을 걸러내세요.**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune은 미국 상장 마이크로캡(micro-cap) 종목을 위한 무료 오픈소스 포렌식 실사(due-diligence) 도구로, API 키가 필요 없습니다.**
이미 보유하고 있거나 관심 있게 지켜보는 종목(ticker)을 지정하면, 각 기업의 SEC 공시에 담긴
리스크 신호와 포렌식 플래그를 드러내 줍니다 -
회계 품질 및 부실(distress) 점수, 희석(dilution) 및 기업 활동(corporate-action) 리스크,
내부자 거래, 8-K 중요 이벤트, 상장폐지 통지 및 진행 중인
거래정지(trading-suspension) 리스크, 그리고 결제 미인도(fails-to-deliver) 정황까지 - **각 기업의 공개된 SEC 공시로부터
산출되므로**, 직접 해당 기업을 평가할 수 있습니다.

이 도구는 전적으로 **공개되고, 계정이 필요 없으며, API 키가 필요 없는 데이터** 위에서 동작합니다. SEC EDGAR가
유일한 데이터 출처입니다(상장 기업 전체 목록, 모든 공시, 그리고
결제 미인도 / 거래정지 피드). **어디에도 자체 키를 제공하는
옵션은 없습니다.**

> PennyTune은 **여러분 자신의 실사를 위한 근거**를 드러내 줍니다 - 어떤 종목이
> "깨끗하다"거나 "지뢰밭"이라고 알려주지 않으며, 매수/매도 조언을 제공하지 않고,
> 결과를 예측하지도 않습니다. 이 도구는 **SEC에 등록된 미국 상장
> 기업**을 분석하며 **실시간 가격은 일절 가져오지 않습니다.** 현재 가격으로
> 선별하거나, 기술적 지표를 계산하거나, 거래 가능성(매수-매도 호가
> 스프레드/유동성)을 평가하지 않습니다. 순위를 매길 종목은 여러분이 직접 제공하며,
> 현재 가격과 거래 가능성은 증권사에서 직접 확인해야 합니다.

---

## ⚠️ 면책 조항 - 반드시 주의 깊게 읽으십시오

PennyTune은 리서치 및 교육용 도구이며, 투자 자문이 아닙니다. 이 도구는 어떠한 증권을 매수, 매도, 또는 보유해야 하는지 알려주지 않습니다. 마이크로캡 및 페니 주식은 투자금의 전액 손실 가능성을 포함하여 극단적인 위험을 수반합니다. 정본에 해당하는 전체 면책 조항은 [영문 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md)에 영어로 제공되며 `pennytune disclaimer` 명령으로도 확인할 수 있습니다.

---

## 무엇인가

미국 마이크로캡 영역에는 *그럴 만한 이유로* 싸 보이는 기업들이 가득합니다 -
현금을 소진하고, 희석하며, 상장폐지에 가깝거나, 조작을 위해 구조화된 기업들 말입니다.
실사의 어려운 부분은 그러한 지뢰를 찾아내기 위해 공시를 읽는 일입니다. PennyTune은
그 읽기를 여러분 대신 수행합니다. 종목(ticker)을 지정하거나, 여러분이 선택한 엄선된
종목 집합의 순위를 매기면, 해당 기업의 SEC 공시에서 리스크 신호와 포렌식 플래그를
추출합니다 - **그 기업의 공개된 SEC 공시로부터 산출됩니다.**

이 도구는 **판결이 아닌 근거**를 드러냅니다. 어떤 종목이 깨끗하다거나 지뢰밭이라고
알려주지 않으며, 매수나 매도를 조언하지 않고, 결과를 예측하지도 않습니다 -
판단은 여러분의 몫입니다.

- **무료이며 API 키 불필요** - 전적으로 계정도, 키도 필요 없는 공개 데이터 위에서 동작합니다.
- **SEC 등록, 미국 주요 거래소(NYSE/NASDAQ/NYSE American)에 상장, OTC는 절대 아님** - 구조적으로 그렇습니다.
- **근거 기반** - 모든 신호는 그 기업의 공개된 SEC 공시로부터 산출되며,
  이벤트 기반 적신호의 경우 해당하는 구체적인 8-K 항목이 명시됩니다.
- **투명하고 조정 가능** - 사용자가 가중치를 편집할 수 있는 분해 가능한 종합
  점수, 선별 프리셋(`penny` 기본값 / `micro` / `small-cap-value` /
  `broad` / `custom`), 그리고 선택 가능한 전략 프로파일(`hold` 기본값 /
  `trader` / `high-return` / `custom`).
- **실시간 가격 없음** - 현재 가격을 가져오거나 거래 가능성을 평가하지 않습니다.
  그것은 증권사에서 직접 확인하십시오.
- **리서치 전용이며, 투자 자문이 아닙니다.**

## 무엇을 드러내는가

각 기업에 대해 PennyTune은 SEC 공시를 읽고 마이크로캡에 가장 중요한 신호들을
등급화합니다 - 모두 그 기업의 공시로부터 산출됩니다:

- **재무 건전성 및 부실(distress)** - Altman Z″ 지급능력 점수와 더불어, 그 기업의
  제출된 재무제표에 대한 포렌식 검사군(Beneish 이익 조작 모델 및 Piotroski
  강건성 모델).
- **희석(dilution) 및 기업 활동** - 셸프(shelf) 및 ATM("시장가" 발행, at-the-market)
  공모, 증가하는 발행 주식 수와 희석 속도, 연쇄적인 액면 병합(reverse-split), 그리고
  8-K 기록에서 도출한 감사인 교체 / 재작성(restatement) 플래그.
- **내부자 거래** - 시장에서의 내부자 *매수*(확신 신호)로, 일상적인 부여(grant) 및
  세금 원천징수와 분명히 구분하여 보상(award)이 결코 강세 신호로 읽히지 않도록 합니다 -
  여기에 더해 Form 144 매도 예정 물량(overhang) 및 13D/13G 지분 활동.
- **8-K 중요 이벤트** - 구조화된 항목 코드 기록(재작성, 감사인 교체, 임원 사임,
  상장 요건 미달 및 기타 중요 항목)으로, 단순 건수가 아니라 심각도에 따라
  가중됩니다.
- **상장폐지 통지 리스크** - 공시된 상장 유지 요건 미달 통지(8-K 항목 3.01)로,
  도구가 계산할 수 없는 가격 시한(price-clock) 일수를 추측하지 않고 보고됩니다.
- **진행 중인 거래정지** - *현재* SEC 거래정지 상태에 있는 기업은 플래그가
  지정되어 제외됩니다. 만료된 과거 거래정지는 정황으로 표시되며, 해당 기업에
  불리하게 적용되지 않습니다.
- **결제 미인도(fails-to-deliver)** - SEC의 격월 결제 미인도 데이터에서 도출한 결제
  스트레스 정황(정황일 뿐 - 그 자체로 조작의 증거는 아닙니다).
- **섹터 분류** - 각 기업의 SIC 섹터로, 품질 및 밸류에이션 비교가 절대적 기준선이
  아니라 섹터 및 규모가 유사한 동종 기업들과 이루어지도록 합니다.

## 데이터 및 출처 표기

PennyTune은 단일 출처에서 공개되고 키가 필요 없는 데이터만 사용합니다: **SEC EDGAR**(전체
목록 - SEC의 `company_tickers_exchange.json` 상장 기업 파일로부터 - 그리고
모든 공시, 재무 펀더멘털, 내부자 양식, 그리고 결제 미인도 /
거래정지 파일). 어디서든 요구되는 유일한 신원 정보는 SEC EDGAR
`User-Agent` 문자열(여러분의 이름 + 이메일)입니다 - 이는 SEC의 공정 접근
정책이 요청자를 식별하기 위해 요구하는 요청 헤더이며, PennyTune 계정, 로그인,
키가 아닙니다. 이 정보는 여러분의 로컬 설정에만 저장되고(`config get`에서는 가려짐),
SEC 요청 헤더로만 전송되며, 저작자나 어떠한 제3자에게도 전송되지 않습니다.
유효한 개인 이메일이면 무엇이든 작동합니다. 설정은 제공자가 아니라 형식을 확인합니다.

PennyTune은 리서치 도구이며 원본 제3자 데이터셋을 재게시하지 **않습니다.** 여러분의
설정과 내보낸 결과는 로컬에 유지됩니다(절대 커밋되지 않음).

## 설치

PennyTune은 PyPI에 게시된 명령줄 도구입니다. 간단하고 보편적인 기본 방법인 pip로
설치하십시오:

```bash
pip install pennytune
```

CLI이므로, **격리된 설치(명령줄 도구에 권장)**를 사용하면 다른 Python 환경과
분리된 상태로 유지됩니다:

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Python 3.11-3.14가 필요합니다(모두 Linux, macOS, Windows 전반에 걸쳐 CI 테스트됨;
3.13이 린팅 및 타입 검사의 주 대상).

**소스에서 설치(개발용):**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## 사용법

최초 설정은 SEC EDGAR 신원 정보(키가 아니라 필수 요청 헤더)와 리스크 동의를
기록합니다. `scan`/`inspect`는 둘 다 존재할 때까지 실행을 거부합니다:

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

주된 작업 흐름은 **`inspect <TICKER>`** 입니다 - 이미 보유하고 있는 기업을
도구에 지정하면, 공시로부터 산출된 전체 포렌식 분석을 얻습니다:

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan`은 **여러분이 선택한 엄선된 종목 집합**의 순위를 - 명시적으로 지정하거나
관심목록(watchlist)에서 읽어 - SEC 공시 리스크 신호에 따라 매깁니다(가격 필터링 없음 -
도구는 가격을 일절 가져오지 않습니다). 한 번에 최대 100개 종목까지이며, PennyTune은
시장 전체를 스캔하는 일이 결코 없습니다. 긍정적 품질 하위 점수들은 섹터/규모 상대
백분위수(대규모 횡단면 전체에서만 의미가 있음)이므로, 소규모 엄선된 집합에서는
순위가 주로 **리스크/페널티** 신호(희석, 부실, 상장폐지, 내부자 매도)에 의해 결정됩니다 -
즉 여러분의 집합에서 가장 위험한 종목들을 드러냅니다. `--preset` / `--profile`로 리스크
가중치와 전략을 조정하십시오:

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

그 밖의 모든 명령:

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

출력은 신선도 헤더(활성 프리셋/프로파일 + 도메인별 기준(as-of) 시점)로 시작하여,
관련이 있을 때 관심목록 알림 배너를 표시하고, 상위 N개의 순위를 매기며, 짧은 면책
조항으로 끝납니다. 내보낸 파일에는 한 줄짜리 면책 조항 헤더가 포함되어 면책 조항이
데이터와 함께 따라다닙니다.

## 개발

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

의존성은 커밋된 `uv.lock`에 해시로 고정되어 있습니다(공급망 규율). 업그레이드는
신중하게 이루어지고 검토되며, 어떤 것도 자동 병합되지 않습니다.

## 라이선스

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ 면책 조항 (반복)

PennyTune은 리서치 및 교육용 도구이며, 투자 자문이 아닙니다. 이 도구는 어떠한 증권을 매수, 매도, 또는 보유해야 하는지 알려주지 않습니다. 마이크로캡 및 페니 주식은 투자금의 전액 손실 가능성을 포함하여 극단적인 위험을 수반합니다. 정본에 해당하는 전체 면책 조항은 [영문 README](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md)에 영어로 제공되며 `pennytune disclaimer` 명령으로도 확인할 수 있습니다.
