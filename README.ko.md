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
- **SEC 등록 공시 기업** - 종목 모집단은 SEC 공개 데이터에서 가져옵니다. 거래소
  필터는 없습니다. OTC 호가 종목도 다른 종목과 똑같이 스캔되며, 근거가 되는 SEC
  파일에는 NYSE American 구분 자체가 없습니다.
- **근거 기반** - 산출되는 신호는 그 기업의 공개된 SEC 공시에서 나오며, 이벤트 기반
  적신호의 경우 해당하는 구체적인 8-K 항목이 명시됩니다. 다만 두 기여 항목, 즉
  밸류에이션과 보도 논조는 이 빌드에 데이터 소스가 없어 항상 억제(suppress)됩니다
  (**한계** 참조).
- **투명하고 조정 가능** - 사용자가 가중치를 편집할 수 있는 분해 가능한 종합
  점수, 선별 프리셋(`penny` 기본값 / `micro` / `small-cap-value` /
  `broad` / `custom`), 그리고 선택 가능한 전략 프로파일(`hold` 기본값 /
  `trader` / `high-return` / `custom`).
- **실시간 가격 없음** - 현재 가격을 가져오거나 거래 가능성을 평가하지 않습니다.
  그것은 증권사에서 직접 확인하십시오.
- **리서치 전용이며, 투자 자문이 아닙니다.**

## 무엇을 드러내는가

각 기업에 대해 PennyTune은 SEC 공시를 읽고 마이크로캡에 가장 중요한 신호들을
등급화합니다. 산출할 수 없는 신호는 억제되고 그렇다고 보고되며, 결코 0점으로
채점되지 않습니다:

- **재무 건전성 및 부실(distress)** - Altman Z″ 지급능력 점수와 더불어, 그 기업의
  제출된 재무제표에 대한 포렌식 검사군(Beneish 이익 조작 모델 및 Piotroski
  강건성 모델).
- **희석(dilution) 및 기업 활동** - 셸프(shelf) 및 ATM("시장가" 발행, at-the-market)
  공모, 증가하는 발행 주식 수와 희석 속도, 연쇄적인 액면 병합(reverse-split), 그리고
  8-K 기록에서 도출한 감사인 교체 / 재작성(restatement) 플래그.
- **내부자 거래** - 시장에서의 내부자 *매수*(확신 신호)로, 일상적인 부여(grant) 및
  세금 원천징수와 분명히 구분하여 보상(award)이 결코 강세 신호로 읽히지 않도록 합니다 -
  여기에 더해 Form 144 매도 예정 물량(overhang) 및 13D/13G 지분 활동.
- **8-K 중요 이벤트** - 구조화된 항목 코드 기록으로, 단순 건수가 아니라 심각도에
  따라 가중됩니다. 발행사가 자사의 기존 공표 재무제표를 더 이상 신뢰할 수 없다고
  밝히는 항목 4.02는 감사인 교체인 항목 4.01과 구분하여 별도로 명시하고 집계하며,
  임원 사임, 상장 요건 미달 및 기타 중요 항목도 함께 다룹니다.
- **상장폐지 통지 리스크** - 공시된 상장 유지 요건 미달 통지(8-K 항목 3.01)로,
  도구가 계산할 수 없는 가격 시한(price-clock) 일수를 추측하지 않고 보고됩니다.
- **거래정지** - 최근 180일 이내에 SEC 거래정지를 받은 기업은 플래그가 지정되어
  제외됩니다. 다만 이 도구는 그 거래정지가 이후 만료되었는지를 추적하지 않습니다.
  SEC 거래정지는 최대 10거래일이므로, 이미 오래전에 만료된 정지를 이유로 종목이
  제외될 수 있습니다.
- **결제 미인도(fails-to-deliver)** - SEC가 월 2회 공표하는 결제 미인도 데이터에서
  도출한 결제 스트레스 정황(정황일 뿐 - 그 자체로 조작의 증거는 아닙니다).
- **SEC 검토의견서(comment letter)** - 최근 1년 사이에 SEC 기업금융국(Division of
  Corporation Finance)이 해당 기업과 서신을 주고받았는지, 그 기간에 해당하는
  의견서와 발행사 답변이 각각 몇 건인지, 그리고 가장 최근 의견서의 날짜.
  정황일 뿐이며 결코 채점에 쓰이지 않습니다. 공시 색인에는 의견서의 존재만
  기록될 뿐 그 주제는 기록되지 않습니다.
- **섹터 분류** - 각 기업의 SIC 섹터를 기록하고 표시합니다. 정황 정보일 뿐이며,
  채점에는 동종 기업 비교가 아니라 고정된 기준 구간을 사용합니다.

## 점수는 어떻게 계산되는가

종합 점수는 **정규화되지 않은 리스크 가중 리서치 점수**입니다:

    종합 = Σ(가중치 x 긍정 하위 점수) - Σ(페널티 x 심각도 x 확신도)

* **긍정 기여 항목**은 **고정된 기준 구간**에 대해 등급화됩니다 - Piotroski 0-9
  척도, Altman Z″ 지급능력 구간, 그리고 고정된 EV/매출 및 매출 성장률 구간입니다.
  따라서 기업의 하위 점수는 오직 그 기업 자신의 공시에만 좌우되며, 같은 실행에 어떤
  종목이 함께 있었는지와는 무관하고, 실행 간 비교가 가능합니다.
* **페널티**는 차감되며, 심각도와 활성 프리셋에 따라 스케일링됩니다.
* **낮을수록 공시에서 도출된 리스크가 더 많이 발견되었다는 뜻입니다.** 밸류에이션도,
  예측도 아니며 목표주가와 비교할 수 있는 값도 아닙니다. 점수가 높다는 것은 "공시에서
  발견된 리스크가 더 적다"는 뜻이지, 결코 "오를 것"이라는 뜻이 아닙니다.
* 점수는 **상·하한이 없고** 고정된 범위도 없습니다. 크기가 아니라 순서로 다루십시오.

**SEC 근거를 전혀 가져오지 못한 종목은 채점되지 않습니다.** `NOT ASSESSED`로 보고되고,
콘솔에 이름이 표시되며, 순위에서 제외됩니다. 근거의 부재가 리스크의 부재로 오해되는
일이 결코 없도록 하기 위함입니다.

**재무 건전성은 Altman의 공표 구간이 아니라 재설정된 기준선을 사용합니다.** Altman Z″는
공표된 계수로 계산하지만, 지급능력 기준선은 공표값 1.1과 2.6이 아니라 **-3.0과 1.0**이며,
하위 점수는 3단계가 아니라 연속적으로 등급화됩니다. 실제 공시 기업 194곳을 대상으로, 각
기업 자신의 연차보고서에 담긴 계속기업(going concern) 관련 문구를 독립적인 부실 라벨로
삼아 측정한 결과: 공표된 기준선에서는 **계속기업 문구가 있는 41곳을 하나도 놓치지 않았지만,
건전한 153곳 중 47곳을 부실로 판정**했습니다 - 그중에는 Starbucks, HP, AbbVie, Amgen,
Oracle, Lowe's, Duke Energy, AT&T가 포함됩니다. 공표된 1.1이라는 경계는 실제 분포의
45백분위수에 위치합니다. 재설정된 기준선은 이 허위 부실 판정률을 31%에서 12%로 낮추면서도,
여전히 계속기업 문구가 있는 어떤 기업도 안전으로 분류하지 않습니다. 이는 공표 모델로부터의
의도적인 이탈입니다.

내보내기에는 `suppressed`, `suppressed_count`, `evidence_complete`, `completeness` 열이
포함되어, 평가된 행과 평가되지 않은 행을 산문을 읽지 않고도 구분할 수 있습니다.

## 한계

순위를 신뢰하기 전에 다음을 읽으십시오.

* **두 기여 항목은 영구적으로 0입니다.** `valuation`과 `sentiment`는 이 빌드에 데이터
  소스가 없습니다 - 시가총액 피드도, 뉴스 피드도 없습니다 - 따라서 모든 기업에 대해,
  모든 실행에서 억제됩니다.
* **대형주의 약 4분의 1에 대해 Altman은 산출할 수 없습니다.** 은행과 REIT는 구분
  대차대조표를 공표하지 않으며, 상당수의 대형 공시 기업은 영업이익 소계를 공표하지
  않습니다. 산출할 수 없는 경우 억제하고 그렇다고 보고하며 결코 대체 추정하지 않습니다 -
  다만 그 종목에서는 재무 건전성 기여 항목이 통째로 빠집니다.
* **대부분의 행은 불완전한 근거 위에 놓여 있습니다.** 대표적인 20종목 스캔에서 18종목은
  실행할 수 없었던 검사가 최소 하나 있었습니다. 그 개수는 행별로 `suppressed_count`
  열이 알려줍니다.
* **이 도구의 순위는 약하며, 권위 있는 것이 아닙니다.** 어느 공시부터 읽을지 정하는 데
  유용합니다. 그대로 실행에 옮길 스크리닝이 아니며, 단일 플래그를 판정으로 취급해서는
  안 됩니다.
* **검토의견서 기록은 이력이지 미결 사안이 아닙니다.** SEC는 검토가 종료된 뒤
  빨라야 20영업일이 지나서야 실무진 의견서를 공개하며, 공시 색인에는 주제가 담기지
  않습니다. 이 도구가 알려줄 수 있는 것은 서신 왕래가 있었다는 사실과 그 시점뿐이며,
  무엇을 질의했는지, 아직 남은 사안이 있는지는 알 수 없습니다. 대응하는 답변 공시가
  없다고 해서 답변하지 않은 것은 아닙니다. 발행사는 흔히 다른 공시 안에서
  답변합니다.
* **관심목록 종목은 첫 실행에서는 결코 알림이 발동하지 않습니다.** 알림은 직전
  스냅샷과 비교해 산출되므로, 최소 두 번 스캔되기 전까지 해당 기업은 아무것도
  올리지 않습니다.
* **캐시가 없습니다.** 실행할 때마다 SEC EDGAR에서 다시 가져옵니다. `config get`이
  표시하는 `cache_ttl` 설정은 아무 작용도 하지 않습니다.

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
시장 전체를 스캔하는 일이 결코 없습니다. 긍정 하위 점수들은 **고정된 기준 구간**에 대해
등급화되므로, 기업의 점수는 같은 실행에 어떤 종목이 함께 있었는지와 무관하며 실행 간
비교가 가능합니다. 그럼에도 순위는 주로 **리스크/페널티** 신호(희석, 부실, 상장폐지,
내부자 매도)에 의해 결정되는데, 공시가 가장 잘 뒷받침하는 것이 그 신호들이기 때문입니다.
`--preset` / `--profile`로 가중치와 전략을 조정하십시오:

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
pennytune watch list          #   run-over-run score deltas
pennytune config get          # view all settings (EDGAR email redacted)
pennytune config set weights.valuation 1.5   # tune a scoring weight
pennytune config set profile custom          # switch to hand-tuned weights
pennytune sources             # data sources, rate limits, contacted domains
```

`scan` 출력은 헤더(활성 프리셋/프로파일 + 데이터 신선도 줄)로 시작하여, 상위 N개의
순위를 매기고, 짧은 면책 조항으로 끝납니다. 내보낸 파일에는 한 줄짜리 면책 조항 헤더가
포함되어 면책 조항이 데이터와 함께 따라다닙니다.

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
