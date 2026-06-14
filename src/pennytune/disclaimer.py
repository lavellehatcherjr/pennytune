"""Legal disclaimer text shipped inside the product.

Three forms are provided, used in their required placements:

* :data:`FULL_DISCLAIMER` - the complete, hardened public-release
  disclaimer. Displayed in full at the interactive ``init`` acknowledgment
  prompt (the user reads it, then types "I UNDERSTAND") and on demand via
  ``pennytune disclaimer`` and the ``--disclaimer`` global flag; also
  reproduced in the README. The non-interactive ``--i-understand-the-risks``
  setup path prints a prominent affirmation pointing back to this text.
* :data:`SHORT_DISCLAIMER` - the short footer appended to every
  ``scan`` / ``inspect`` output (unconditional, shown even under ``--quiet``).
* :data:`EXPORT_HEADER` - the one-line header written into every
  exported file so the disclaimer travels with the data.

The text is reproduced verbatim and must not be abridged, summarized, or
otherwise altered.
"""

from __future__ import annotations

__all__ = ["FULL_DISCLAIMER", "SHORT_DISCLAIMER", "EXPORT_HEADER"]

# Full disclaimer (first run + `pennytune disclaimer` + README).
FULL_DISCLAIMER = """\
DISCLAIMER — PLEASE READ CAREFULLY

1. NOT INVESTMENT ADVICE. PennyTune is a research and educational tool
only. Nothing it produces is investment advice, financial advice, legal
advice, tax advice, trading advice, or a recommendation, offer, or
solicitation to buy, sell, or hold any security or to make any financial
transaction. Rankings, scores, signals, and any other output are the
result of automated rules applied to public data and are provided for
informational and educational purposes only.

2. NO ADVISER RELATIONSHIP; NOT REGISTERED. The author is not a licensed
or registered financial advisor, investment adviser, broker, broker-
dealer, or investment professional, and is not registered with the U.S.
Securities and Exchange Commission, FINRA, or any state or other
securities regulator. Use of this software creates no advisory,
fiduciary, brokerage, agency, or professional relationship of any kind
between you and the author. The author is not acting as a fiduciary to
you.

3. NO RELIANCE. You agree not to rely on this software or its output as
the basis for any investment, trading, or financial decision. Any and
all decisions you make are made solely by you, in your own independent
judgment, and at your own risk. You are solely and exclusively
responsible for your own investment decisions and their consequences.

4. EXTREME RISK OF PENNY STOCKS. Penny stocks and low-priced, micro-cap,
and sub-$1 securities are highly speculative and carry a substantial
risk of loss, up to and including the TOTAL LOSS of your investment.
They are subject to low liquidity, extreme volatility, wide bid-ask
spreads, limited or unreliable public information, fraud, market
manipulation (including pump-and-dump schemes), dilution, reverse
splits, trading halts, suspensions, and delisting. You should not invest
any money you cannot afford to lose entirely.

5. NO GUARANTEE; FORWARD-LOOKING. Scores, rankings, and signals are NOT
predictions and do NOT guarantee any outcome or result. Past performance
is not indicative of, and does not guarantee, future results. No
representation is made that any account will or is likely to achieve
profits or losses similar to any analysis, backtest, or example shown.

6. THIRD-PARTY DATA "AS IS." All data is obtained from third-party and
public sources (including SEC EDGAR, GDELT, and other public sources)
and is provided "AS IS." Such data may be inaccurate,
incomplete, delayed, out of date, or wrong. The author does not create,
endorse, verify, or guarantee any third-party data and makes no
representation or warranty as to its accuracy, completeness, timeliness,
or fitness. You must independently verify all information against primary
sources (such as official SEC filings) before acting on it.

7. NO WARRANTY. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE
SOFTWARE IS PROVIDED "AS IS" AND "AS AVAILABLE," WITHOUT WARRANTY OF ANY
KIND, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE,
ACCURACY, AND NONINFRINGEMENT. THE AUTHOR DOES NOT WARRANT THAT THE
SOFTWARE WILL BE UNINTERRUPTED, ERROR-FREE, SECURE, OR THAT DEFECTS WILL
BE CORRECTED.

8. LIMITATION OF LIABILITY. TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE
LAW, IN NO EVENT SHALL THE AUTHOR OR ANY CONTRIBUTOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE, OR
CONSEQUENTIAL DAMAGES, OR FOR ANY LOSS OF PROFITS, REVENUE, DATA, OR
INVESTMENT OR TRADING LOSSES, ARISING OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR ITS USE OR OUTPUT, WHETHER IN AN ACTION OF CONTRACT, TORT
(INCLUDING NEGLIGENCE), STRICT LIABILITY, OR OTHERWISE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGES. THIS LIMITATION APPLIES REGARDLESS OF
THE FAILURE OF ANY ESSENTIAL PURPOSE OF ANY LIMITED REMEDY.

9. INDEMNIFICATION. You agree to indemnify, defend, and hold harmless the
author and any contributors from and against any and all claims,
liabilities, damages, losses, costs, and expenses (including reasonable
legal fees) arising out of or related to your use of the software, your
investment or trading decisions, or your violation of this disclaimer.

10. COMPLIANCE. You are responsible for complying with all laws,
regulations, and rules applicable to you, including securities laws and
the terms of service of any data provider. The software is intended for
lawful personal and educational use only.

11. SEVERABILITY. If any provision of this disclaimer is held to be
invalid or unenforceable, that provision shall be limited or eliminated
to the minimum extent necessary, and the remaining provisions shall
remain in full force and effect.

12. ACCEPTANCE. By installing, accessing, or using PennyTune, you
acknowledge that you have read, understood, and agree to this entire
disclaimer, and that you use the software entirely at your own risk. If
you do not agree, do not install or use the software."""

# Short form - the footer appended to every `scan` / `inspect` output.
SHORT_DISCLAIMER = """\
Research and educational tool only. Not investment advice. Penny stocks
are high-risk and may result in total loss. Data may be inaccurate or
delayed. Verify against primary sources. Use at your own risk."""

# Export header - the one line written into CSV/Parquet/JSON/Markdown exports.
EXPORT_HEADER = (
    "# PennyTune — research/educational only; not investment advice; "
    "data may be inaccurate/delayed; verify against primary sources; "
    "use at your own risk."
)
