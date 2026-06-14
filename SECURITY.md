# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities **privately** via GitHub's private
vulnerability reporting — do **not** open a public issue for a vulnerability:

- **<https://github.com/lavellehatcherjr/pennytune/security/advisories/new>**

PennyTune is maintained by a single author; please allow reasonable time for a
fix before public disclosure.

## Supported Versions

Only the latest released version receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Model

PennyTune is a local command-line tool that fetches public data from SEC EDGAR
and GDELT. Its security posture:

- **No API keys, accounts, or secrets.** PennyTune uses no API keys and requires
  no account anywhere, and has no secret store or keyring — there are no
  credentials to leak.
- **Minimal local identity, redacted on display.** The only identity is the SEC
  EDGAR contact (your name + email) that the SEC's fair-access policy requires in
  the request `User-Agent`. It is stored only in your local config file, and the
  email is masked in `config get` / `config set` output (e.g. `Name
  <d***@domain>`).
- **HTTPS-only, allow-listed network access.** The tool connects only to SEC
  EDGAR and GDELT, over HTTPS; non-HTTPS and off-allow-list requests are
  rejected. The egress allow-list is `sec.gov` and `gdeltproject.org` — nothing
  else.
- **No telemetry.** PennyTune does not phone home and sends no analytics or usage
  data.
- **Defensive parsing.** SEC XML is parsed with `defusedxml`; the standard-library
  XML parser and `pickle` are forbidden, guarding against XML-based and
  deserialization attacks.
- **Supply-chain discipline.** Dependencies are hash-pinned in a committed
  `uv.lock`. Updates flow through Dependabot, run the full cross-platform CI
  matrix plus `pip-audit`, and are reviewed — nothing is auto-merged.
- **Responsible access.** SEC requests are rate-limited (the SEC asks for no more
  than 10 requests/second; the tool enforces this).
- **Enforced in CI.** These properties are asserted by an automated
  security-invariants test suite that runs on every change — no forbidden
  imports, no `eval` / `exec` / `os.system`, HTTPS-only egress to the two
  documented domains, no secret-bearing config fields, and the presence of the
  legal disclaimer and the required source attributions.

## Known Limitations

- **Data sent to the SEC.** To access SEC EDGAR, PennyTune sends your contact
  identity (name + email) to the SEC in the request `User-Agent`, as the SEC's
  fair-access policy requires. GDELT requests use a generic, keyless
  `User-Agent`, so your email is sent **only** to the SEC.
- **Third-party public data, as is.** All analysis data comes from third-party
  public sources (SEC EDGAR, GDELT) and is provided "as is"; PennyTune does not
  control those services' availability or the accuracy of their data. The full
  disclaimer (`pennytune disclaimer`) covers data caveats — PennyTune surfaces
  evidence for your own due diligence and is not investment advice.
