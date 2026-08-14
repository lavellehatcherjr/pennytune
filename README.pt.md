<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> Nota: Esta é uma tradução fornecida apenas para fins informativos. O [README em inglês](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) é a versão oficial e autoritativa. A interface, os comandos e a saída do PennyTune estão disponíveis somente em inglês. Em caso de qualquer divergência, prevalece a versão em inglês.

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | [Français](https://github.com/lavellehatcherjr/pennytune/blob/main/README.fr.md) | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | Português | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

# PennyTune

**Silencie o ruído.**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**O PennyTune é uma ferramenta gratuita, de código aberto e sem chaves de API para due diligence forense de micro-caps listadas nos EUA.**
Aponte-o para os tickers que você já possui ou está acompanhando e ele revela os
sinais de risco e os indícios forenses presentes nos registros (filings) da SEC de cada empresa -
scores de qualidade contábil e de estresse financeiro (distress), risco de diluição e de ações corporativas,
atividade de insiders, eventos materiais em 8-K, risco de aviso de deslistagem (delisting) e de
suspensão de negociação ativa, além do contexto de liquidação de fails-to-deliver - **calculados
a partir dos registros públicos da SEC de cada empresa**, para que você mesmo possa avaliar a empresa.

Ele funciona inteiramente com **dados públicos, sem conta e sem chaves de API**: a SEC EDGAR é a
única fonte de dados (o universo de empresas listadas, todos os registros e os
feeds de fails-to-deliver / suspensão de negociação). **Não há, em lugar nenhum, opção de usar a sua própria
chave (bring-your-own-key)**.

> O PennyTune revela **evidências para a sua própria due diligence** - ele não diz
> se uma ação é "limpa" ou "uma bomba-relógio", não dá conselhos de compra/venda
> e não prevê resultados. Ele analisa **empresas listadas nos EUA e registradas na
> SEC** e **não busca cotações ao vivo**: ele não filtra por preço
> atual, não calcula indicadores técnicos nem avalia a negociabilidade (spread
> entre compra e venda / liquidez). Você fornece o(s) ticker(s) a classificar e verifica o preço atual
> e a negociabilidade você mesmo em uma corretora.

---

## ⚠️ Aviso legal - leia com atenção

O PennyTune é uma ferramenta de pesquisa e educação, não um conselho de investimento. Ele não diz se você deve comprar, vender ou manter qualquer valor mobiliário. Micro-caps e penny stocks carregam risco extremo, incluindo a possível perda total do seu capital. O aviso legal completo, que é a versão de referência, está disponível em inglês no [README em inglês](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) e por meio do comando `pennytune disclaimer`.

---

## O que é

O segmento de micro-caps dos EUA está repleto de empresas que parecem baratas *por um motivo* -
queimando caixa, diluindo, à beira da deslistagem ou estruturadas para manipulação. A parte difícil
da due diligence é ler os registros para encontrar essas bombas-relógio. O PennyTune
faz essa leitura por você: aponte-o para um ticker, ou classifique um conjunto curado de
tickers escolhidos por você, e ele extrai os sinais de risco e os indícios forenses
dos registros da SEC da empresa - **calculados a partir dos registros públicos da SEC
da empresa**.

Ele revela **evidências, não veredictos.** Ele não diz se uma ação é limpa ou
uma bomba-relógio, não aconselha comprar ou vender e não prevê resultados -
o julgamento é seu.

- **Gratuito e sem chaves de API** - funciona inteiramente com dados públicos, sem conta e sem chave.
- **Empresas registradas na SEC** - o universo de tickers vem de dados públicos da SEC.
  Não há filtro por bolsa: nomes cotados em OTC são varridos como quaisquer outros, e o
  arquivo da SEC em que isso se baseia não traz designação NYSE American.
- **Baseado em evidências** - os sinais que são calculados vêm dos registros públicos da
  SEC da empresa e, para os sinais de alerta (red flags) orientados por eventos, o item
  específico do 8-K é nomeado. Dois contribuintes, valuation e tom da cobertura, não têm
  fonte de dados nesta build e são sempre suprimidos (ver **Limitações**).
- **Transparente e ajustável** - um score composto decomponível com pesos
  editáveis pelo usuário, presets de triagem (`penny` padrão / `micro` / `small-cap-value` /
  `broad` / `custom`) e perfis de estratégia selecionáveis (`hold` padrão /
  `trader` / `high-return` / `custom`).
- **Sem cotações ao vivo** - ele não busca o preço atual nem avalia a negociabilidade;
  verifique isso você mesmo em uma corretora.
- **Apenas pesquisa, não é conselho de investimento.**

## O que ele revela

Para cada empresa, o PennyTune lê os registros da SEC e avalia os sinais que
mais importam para uma micro-cap. Todo sinal que ele não consegue calcular é suprimido e
reportado como tal, nunca pontuado como zero:

- **Saúde financeira e estresse (distress)** - pontuação de solvência Altman Z″ mais uma
  bateria forense (modelos de manipulação de lucros de Beneish e de força de Piotroski) sobre as
  demonstrações financeiras registradas da empresa.
- **Diluição e ações corporativas** - ofertas em prateleira (shelf) e ATM ("at-the-market"),
  aumento na contagem de ações e velocidade de diluição, grupamentos (reverse splits) em série e
  sinais de troca de auditor / republicação de demonstrações (restatement) extraídos do histórico de 8-K.
- **Atividade de insiders** - *compra* de insiders em mercado aberto (o sinal de convicção),
  mantida distinta de outorgas rotineiras e de retenção para fins tributários, de modo que prêmios nunca sejam lidos como
  altistas - além do overhang de venda proposta no Form 144 e da atividade de propriedade em 13D/13G.
- **Eventos materiais em 8-K** - a fita estruturada de códigos de item, ponderada por
  severidade em vez de contagem bruta. O Item 4.02, com o qual o emissor declara que suas
  próprias demonstrações financeiras já publicadas não podem mais ser consideradas
  confiáveis, é nomeado e contado separadamente do Item 4.01, uma troca de auditor, ao
  lado das saídas de executivos, da deficiência de listagem e dos demais itens materiais.
- **Risco de aviso de deslistagem** - avisos divulgados de deficiência de manutenção de listagem
  (8-K Item 3.01), reportados sem adivinhar a contagem de dias do prazo de preço (price-clock) que a ferramenta
  não consegue calcular.
- **Suspensões de negociação** - uma empresa com uma suspensão de negociação da SEC nos
  últimos 180 dias é sinalizada e separada. Note que a ferramenta não acompanha se a
  suspensão já caducou: suspensões da SEC duram no máximo 10 pregões, então um nome pode
  ficar de fora por uma suspensão expirada há muito tempo.
- **Fails-to-deliver** - contexto de estresse de liquidação a partir dos dados de
  fails-to-deliver que a SEC publica duas vezes por mês (apenas contexto - não é, por si
  só, evidência de manipulação).
- **Comment letters da SEC** - se a Division of Corporation Finance manteve
  correspondência com a empresa no último ano, quantas cartas e quantas respostas do
  emissor caem nessa janela, e a data da carta mais recente. Apenas contexto, nunca
  pontuado. O índice de registros anota a carta, mas não o seu assunto.
- **Classificação setorial** - o setor SIC de cada empresa é registrado e exibido. É
  apenas contexto: a pontuação usa faixas de referência fixas, não comparação com pares.

## Como o score funciona

O composto é um **score de pesquisa ponderado por risco e não normalizado**:

    composto = soma(peso x sub-score positivo) - soma(penalidade x severidade x confiança)

* Os **contribuintes positivos** são avaliados contra **faixas de referência fixas**: a
  escala Piotroski 0-9, as zonas de solvência Altman Z″ e faixas fixas de EV/Receita e de
  crescimento de receita. O sub-score de uma empresa depende, portanto, apenas dos seus
  próprios registros, não de quais outros tickers estavam na execução, e é comparável
  entre execuções.
* As **penalidades** subtraem, escaladas por severidade e pelo preset ativo.
* **Mais baixo significa que mais risco derivado dos registros foi encontrado.** Não é um
  valuation, não é uma previsão e não é comparável a um preço-alvo. Um score alto
  significa "menos risco foi encontrado nos registros", nunca "isto vai subir".
* O score **não é limitado** e não tem faixa fixa; trate-o como uma ordenação, não como
  uma magnitude.

**Um ticker sem nenhuma evidência da SEC obtida não é pontuado.** Ele é reportado como
`NOT ASSESSED`, nomeado no console e excluído da classificação, de modo que a ausência de
evidência nunca seja confundida com ausência de risco.

**A saúde financeira usa cortes reancorados, não as faixas publicadas de Altman.** O
Altman Z″ é calculado com seus coeficientes publicados, mas os cortes de solvência são
**-3,0 e 1,0**, não os publicados 1,1 e 2,6, e o sub-score é avaliado de forma contínua em
vez de em três degraus. Medido sobre 194 empresas reais, usando a linguagem de continuidade
operacional (going concern) no relatório anual de cada empresa como rótulo independente de
estresse: nos cortes publicados **nenhuma das 41 empresas com going concern foi perdida,
mas 47 de 153 empresas saudáveis foram classificadas como em estresse** - entre elas
Starbucks, HP, AbbVie, Amgen, Oracle, Lowe's, Duke Energy e AT&T. O limite publicado de 1,1
fica no percentil 45 da distribuição real. Os cortes reancorados reduzem essa taxa de falso
estresse de 31% para 12% e continuam a não classificar nenhuma empresa com going concern
como segura. É um afastamento deliberado do modelo publicado.

As exportações trazem as colunas `suppressed`, `suppressed_count`, `evidence_complete` e
`completeness`, de modo que uma linha avaliada se distinga de uma não avaliada sem ler prosa.

## Limitações

Leia-as antes de confiar em uma classificação.

* **Dois contribuintes são permanentemente zero.** `valuation` e `sentiment` não têm fonte
  de dados nesta build - não há feed de valor de mercado nem de notícias - então são
  suprimidos para toda empresa, em toda execução.
* **O Altman não é calculável para cerca de um quarto das large caps.** Bancos e REITs não
  publicam balanço classificado, e diversas empresas grandes não publicam subtotal de
  resultado operacional. Onde não é calculável, é suprimido e reportado, nunca imputado -
  mas o contribuinte de saúde financeira falta por completo para aquele nome.
* **A maioria das linhas se apoia em evidências incompletas.** Em uma varredura
  representativa de 20 nomes, 18 tinham ao menos uma verificação que não pôde ser
  executada. A coluna `suppressed_count` informa quantas, por linha.
* **A ferramenta classifica de forma fraca, não autoritativa.** Serve para decidir quais
  registros ler primeiro. Não é uma triagem sobre a qual agir diretamente, e nenhum sinal
  isolado deve ser tratado como veredito.
* **A atividade de comment letters é histórico, não uma questão em aberto.** A SEC
  divulga uma carta da equipe no mínimo 20 dias úteis depois de encerrada a revisão, e o
  índice de registros não traz o assunto. A ferramenta pode dizer que houve
  correspondência e quando; não pode dizer o que foi perguntado nem se algo continua
  pendente. Uma carta sem um registro de resposta associado não é uma carta sem resposta:
  os emissores costumam responder dentro de outro registro.
* **Um nome acompanhado nunca alerta na primeira execução.** Os alertas são calculados
  contra o snapshot anterior, então uma empresa não levanta nada até ter sido escaneada
  ao menos duas vezes.
* **Sem cache.** Cada execução baixa novamente do SEC EDGAR. Os ajustes `cache_ttl`
  exibidos por `config get` são inertes.

## Dados e atribuição

O PennyTune usa apenas dados públicos, sem chave, de uma única fonte: a **SEC EDGAR** (o
universo - a partir do arquivo de empresas listadas `company_tickers_exchange.json` da SEC - e
todos os registros, fundamentos, formulários de insiders e os arquivos de fails-to-deliver /
suspensão de negociação). A única identificação exigida em qualquer lugar é a string
`User-Agent` da SEC EDGAR (seu nome + e-mail) - um cabeçalho de requisição que a política de acesso
justo (fair-access) da SEC exige para identificar o solicitante, e não uma conta, login ou chave do
PennyTune. Ela é armazenada apenas na sua configuração local (ocultada em `config get`), enviada apenas
no cabeçalho de requisição da SEC, e nunca transmitida ao autor ou a qualquer terceiro.
Qualquer e-mail pessoal válido funciona; a configuração verifica o formato, não o provedor.

O PennyTune é uma ferramenta de pesquisa e **não** republica conjuntos de dados brutos de terceiros;
sua configuração e quaisquer resultados exportados permanecem locais (nunca são versionados no repositório).

## Instalação

O PennyTune é uma ferramenta de linha de comando publicada no PyPI. Instale-a com o pip - o
padrão simples e universal:

```bash
pip install pennytune
```

Por ser uma CLI, uma **instalação isolada (recomendada para ferramentas de linha de comando)**
a mantém fora dos seus outros ambientes Python:

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Requer Python 3.11-3.14 (todos testados em CI no Linux, macOS e Windows; o 3.13
é o alvo principal para linting e verificação de tipos).

**A partir do código-fonte (para desenvolvimento):**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## Uso

A configuração inicial registra a identidade da SEC EDGAR (um cabeçalho de requisição obrigatório - não
uma chave) e a confirmação de risco; `scan`/`inspect` se recusam a executar até que ambos
existam:

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

O fluxo de trabalho principal é **`inspect <TICKER>`** - aponte a ferramenta para uma empresa que
você já possui e obtenha sua análise forense completa calculada a partir dos registros:

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

O `scan` classifica um **conjunto curado de tickers escolhidos por você** - fornecidos explicitamente ou lidos
da sua watchlist - pelos seus sinais de risco nos registros da SEC (sem filtragem por preço - a
ferramenta não busca preços). No máximo 100 tickers por execução; o PennyTune nunca varre o
mercado inteiro. Os sub-scores positivos são avaliados contra **faixas de referência fixas**,
então o score de uma empresa não depende de quais outros tickers estavam na execução e é
comparável entre execuções. Ainda assim, a classificação é determinada principalmente pelos
sinais de **risco/penalidade** (diluição, distress, deslistagem, venda de insiders), pois são
os que os registros melhor sustentam. Ajuste a ponderação e a estratégia com
`--preset` / `--profile`:

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

Todos os demais comandos:

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

A saída do `scan` começa com um cabeçalho (preset/profile ativo + linhas de atualidade dos
dados), classifica os N primeiros e termina com o aviso legal resumido. Os arquivos
exportados carregam o cabeçalho de aviso legal de uma linha, de modo que o aviso legal
acompanhe os dados.

## Desenvolvimento

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

As dependências têm hashes fixados (hash-pinned) em um `uv.lock` versionado (disciplina de cadeia de suprimentos).
As atualizações são deliberadas e revisadas; nada é mesclado automaticamente.

## Licença

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ Aviso legal (repetido)

O PennyTune é uma ferramenta de pesquisa e educação, não um conselho de investimento. Ele não diz se você deve comprar, vender ou manter qualquer valor mobiliário. Micro-caps e penny stocks carregam risco extremo, incluindo a possível perda total do seu capital. O aviso legal completo, que é a versão de referência, está disponível em inglês no [README em inglês](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) e por meio do comando `pennytune disclaimer`.
