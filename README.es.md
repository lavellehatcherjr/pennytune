<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> Nota: Esta es una traducción proporcionada únicamente con fines informativos. El [README en inglés](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) es la versión oficial y autoritativa. La interfaz, los comandos y la salida de PennyTune están disponibles solo en inglés. En caso de cualquier discrepancia, prevalece la versión en inglés.

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | Español | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

# PennyTune

**Silencia el ruido.**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune es una herramienta forense de diligencia debida (due diligence), gratuita, de código abierto y sin claves de API, para micro-caps cotizadas en EE. UU.**
Apúntala a los tickers que ya posees o que estás vigilando y hará aflorar las
señales de riesgo y los indicadores forenses (red flags) en las presentaciones
ante la SEC de cada empresa: puntuaciones de calidad contable y de insolvencia,
riesgo de dilución y de operaciones societarias (corporate actions), actividad de
insiders, eventos materiales del 8-K, riesgo de aviso de exclusión de cotización
(delisting) y de suspensión activa de la negociación, y el contexto de
liquidaciones por fallos de entrega (fails-to-deliver), **calculado a partir de
las presentaciones públicas de cada empresa ante la SEC**, para que puedas evaluar
la empresa por ti mismo.

Funciona enteramente con **datos públicos, sin cuenta y sin claves de API**: SEC
EDGAR es la única fuente de datos (el universo de empresas cotizadas, todas las
presentaciones y los feeds de fails-to-deliver / suspensión de negociación). **No
existe en ninguna parte la opción de aportar tu propia clave (bring-your-own-key)**.

> PennyTune hace aflorar **evidencia para tu propia diligencia debida**: no te
> dice si una acción está "limpia" o es "una mina terrestre", no da consejos de
> compra/venta y no predice resultados. Analiza **empresas cotizadas en EE. UU.
> registradas ante la SEC** y **no obtiene precios en vivo**: no filtra por el
> precio actual, no calcula indicadores técnicos ni evalúa la negociabilidad
> (diferencial de compra-venta / liquidez). Tú proporcionas el o los tickers a
> clasificar, y verificas tú mismo el precio actual y la negociabilidad en una
> correduría.

---

## ⚠️ Aviso legal - léelo con atención

PennyTune es una herramienta de investigación y educación, no asesoramiento de inversión. No te dice si debes comprar, vender o mantener ningún valor. Las micro-caps y las penny stocks conllevan un riesgo extremo, incluida la posible pérdida total de tu capital. El aviso legal completo, que es la versión autorizada y de referencia, está disponible en inglés en el [README en inglés](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) y mediante el comando `pennytune disclaimer`.

---

## Qué es

El segmento de las micro-caps de EE. UU. está lleno de empresas que parecen
baratas *por una razón*: que queman caja, que diluyen, cerca de la exclusión de
cotización (delisting) o estructuradas para la manipulación. La parte difícil de
la diligencia debida es leer las presentaciones para encontrar esas minas
terrestres. PennyTune hace esa lectura por ti: apúntala a un ticker, o clasifica
un conjunto curado de tickers que tú elijas, y extraerá las señales de riesgo y
los indicadores forenses (red flags) de las presentaciones ante la SEC de la
empresa, **calculado a partir de las presentaciones públicas de la empresa ante
la SEC**.

Hace aflorar **evidencia, no veredictos.** No te dice que una acción esté limpia
o sea una mina terrestre, no aconseja comprar o vender, y no predice resultados:
el juicio es tuyo.

- **Gratuito y sin claves de API**: funciona enteramente con datos públicos, sin
  cuenta y sin clave.
- **Registrada ante la SEC, cotizada en una bolsa importante de EE. UU. (NYSE/NASDAQ/NYSE American), nunca OTC**: por construcción.
- **Basado en evidencia**: cada señal se calcula a partir de las presentaciones
  públicas de la empresa ante la SEC y, para las red flags impulsadas por
  eventos, se nombra el ítem específico del 8-K.
- **Transparente y ajustable**: una puntuación compuesta descomponible con pesos
  editables por el usuario, presets de cribado (`penny` por defecto / `micro` /
  `small-cap-value` / `broad` / `custom`) y perfiles de estrategia seleccionables
  (`hold` por defecto / `trader` / `high-return` / `custom`).
- **Sin precios en vivo**: no obtiene el precio actual ni evalúa la
  negociabilidad; verifícalos tú mismo en una correduría.
- **Solo investigación, no es asesoramiento de inversión.**

## Qué hace aflorar

Para cada empresa, PennyTune lee las presentaciones ante la SEC y califica las
señales que más importan para una micro-cap, cada una de ellas calculada a partir
de las presentaciones de la empresa:

- **Salud financiera e insolvencia**: puntuación de solvencia Altman Z″ más una
  batería forense (los modelos de manipulación de beneficios de Beneish y de
  fortaleza de Piotroski) sobre los estados financieros presentados por la
  empresa.
- **Dilución y operaciones societarias (corporate actions)**: ofertas en
  estantería (shelf) y ATM ("at-the-market"), conteos de acciones crecientes y
  velocidad de dilución, reverse splits en serie, e indicadores de cambio de
  auditor / reexpresión (restatement) extraídos del registro de 8-K.
- **Actividad de insiders**: *compras* de insiders en el mercado abierto (la
  señal de convicción), mantenidas separadas de las concesiones rutinarias y de
  la retención fiscal para que las adjudicaciones (awards) nunca se interpreten
  como alcistas, más el sobrante (overhang) de ventas propuestas del Form 144 y
  la actividad de propiedad 13D/13G.
- **Eventos materiales del 8-K**: la cinta estructurada de códigos de ítem
  (reexpresiones, cambios de auditor, salidas de directivos, deficiencias de
  cotización y otros ítems materiales), ponderada por gravedad en lugar de por
  conteo bruto.
- **Riesgo de aviso de exclusión de cotización (delisting)**: avisos de
  deficiencia de cotización continuada divulgados (8-K Ítem 3.01), reportados sin
  adivinar el conteo de días del reloj de precios (price-clock) que la herramienta
  no puede calcular.
- **Suspensiones activas de la negociación**: una empresa bajo una suspensión de
  negociación *vigente* de la SEC se marca y se excluye; las suspensiones
  históricas vencidas se muestran como contexto, no en contra de la empresa.
- **Fails-to-deliver**: contexto de estrés de liquidación a partir de los datos
  bimensuales de fails-to-deliver de la SEC (solo contexto, no es evidencia de
  manipulación por sí solo).
- **Clasificación sectorial**: el sector SIC de cada empresa, de modo que las
  comparaciones de calidad y valoración se hagan frente a pares de sector y tamaño
  en lugar de cortes absolutos.

## Datos y atribución

PennyTune utiliza únicamente datos públicos, sin clave, de una sola fuente: **SEC
EDGAR** (el universo, a partir del archivo de empresas cotizadas
`company_tickers_exchange.json` de la SEC, y todas las presentaciones,
fundamentales, formularios de insiders y los archivos de fails-to-deliver /
suspensión de negociación). La única identidad requerida en cualquier parte es la
cadena `User-Agent` de SEC EDGAR (tu nombre + correo electrónico): un encabezado
de solicitud que la política de acceso justo de la SEC exige para identificar al
solicitante, no una cuenta, inicio de sesión o clave de PennyTune. Se almacena
solo en tu configuración local (redactado en `config get`), se envía solo en el
encabezado de la solicitud a la SEC, y nunca se transmite al autor ni a ningún
tercero. Funciona cualquier correo electrónico personal válido; la configuración
verifica el formato, no el proveedor.

PennyTune es una herramienta de investigación y **no** vuelve a publicar
conjuntos de datos brutos de terceros; tu configuración y cualquier resultado
exportado permanecen en local (nunca se confirman en el repositorio).

## Instalación

PennyTune es una herramienta de línea de comandos publicada en PyPI. Instálala con
pip, la opción predeterminada simple y universal:

```bash
pip install pennytune
```

Como es una CLI, una **instalación aislada (recomendada para herramientas de línea
de comandos)** la mantiene fuera de tus otros entornos de Python:

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Requiere Python 3.11-3.14 (todas probadas en CI a través de Linux, macOS y
Windows; 3.13 es el objetivo principal para el linting y la comprobación de
tipos).

**Desde el código fuente (para desarrollo):**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## Uso

La configuración inicial registra la identidad de SEC EDGAR (un encabezado de
solicitud requerido, no una clave) y el reconocimiento del riesgo; `scan`/`inspect`
se niegan a ejecutarse hasta que ambos existan:

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

El flujo de trabajo principal es **`inspect <TICKER>`**: apunta la herramienta a
una empresa que ya tienes y obtén su desglose forense completo calculado a partir
de las presentaciones:

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` clasifica un **conjunto curado de tickers que tú elijas** (dados de forma
explícita o leídos de tu lista de seguimiento) por sus señales de riesgo de las
presentaciones ante la SEC (sin filtrado por precio: la herramienta no obtiene
precios). Como máximo 100 tickers por ejecución; PennyTune nunca escanea todo el
mercado. Dado que las subpuntuaciones de calidad positivas son percentiles
relativos al sector/tamaño (significativos solo a través de una gran sección
transversal), en un conjunto curado pequeño la clasificación se rige
principalmente por las señales de **riesgo/penalización** (dilución, insolvencia,
delisting, ventas de insiders): hace aflorar los nombres más arriesgados de tu
conjunto. Ajusta la ponderación del riesgo y la estrategia con `--preset` /
`--profile`:

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

Todos los demás comandos:

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

La salida comienza con un encabezado de actualidad (preset/perfil activo + marcas
de "a fecha de" (as-of) por dominio), muestra un banner de alerta de la lista de
seguimiento cuando es relevante, clasifica los N principales y termina con el
aviso legal breve. Los archivos exportados llevan el encabezado de aviso legal de
una línea, de modo que el aviso legal viaja con los datos.

## Desarrollo

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

Las dependencias están fijadas por hash en un `uv.lock` confirmado en el
repositorio (disciplina de cadena de suministro). Las actualizaciones son
deliberadas y revisadas; nada se fusiona automáticamente.

## Licencia

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ Aviso legal (repetido)

PennyTune es una herramienta de investigación y educación, no asesoramiento de inversión. No te dice si debes comprar, vender o mantener ningún valor. Las micro-caps y las penny stocks conllevan un riesgo extremo, incluida la posible pérdida total de tu capital. El aviso legal completo, que es la versión autorizada y de referencia, está disponible en inglés en el [README en inglés](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) y mediante el comando `pennytune disclaimer`.
