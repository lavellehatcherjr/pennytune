<p align="center">
  <img src="https://raw.githubusercontent.com/lavellehatcherjr/pennytune/main/docs/assets/pennytune-logo.png" alt="PennyTune" width="400">
</p>

> Note : ceci est une traduction fournie à titre purement informatif. Le [README en anglais](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) est la version officielle et faisant foi. L'interface, les commandes et les sorties de PennyTune sont disponibles uniquement en anglais. En cas de divergence, la version anglaise prévaut.

[English](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) | [日本語](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ja.md) | [Español](https://github.com/lavellehatcherjr/pennytune/blob/main/README.es.md) | Français | [한국어](https://github.com/lavellehatcherjr/pennytune/blob/main/README.ko.md) | [中文](https://github.com/lavellehatcherjr/pennytune/blob/main/README.zh.md) | [Deutsch](https://github.com/lavellehatcherjr/pennytune/blob/main/README.de.md) | [Português](https://github.com/lavellehatcherjr/pennytune/blob/main/README.pt.md) | [Italiano](https://github.com/lavellehatcherjr/pennytune/blob/main/README.it.md)

# PennyTune

**Faites taire le bruit.**

[![CI](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml/badge.svg)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pennytune)](https://pypi.org/project/pennytune/)
[![Downloads](https://img.shields.io/pepy/dt/pennytune)](https://pepy.tech/project/pennytune)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/platforms-Mac%20%7C%20Windows%20%7C%20Linux-blue)](https://github.com/lavellehatcherjr/pennytune/actions/workflows/ci.yml)

**PennyTune est un outil de due diligence forensique gratuit, open-source et sans clé d'API, dédié aux micro-capitalisations cotées aux États-Unis.**
Pointez-le sur les tickers que vous détenez déjà ou que vous surveillez, et il
fait ressortir les signaux de risque et les indicateurs forensiques dans les
dépôts SEC de chaque société - scores de qualité comptable et de détresse
financière, risque de dilution et d'opérations sur titres, activité des initiés,
événements importants des 8-K, risque d'avis de radiation et de suspension de
négociation active, ainsi que le contexte de règlement-livraison
(fails-to-deliver) - **calculés à partir des dépôts SEC publics de chaque
société**, afin que vous puissiez évaluer la société par vous-même.

Il fonctionne entièrement à partir de **données publiques, sans compte et sans
clé d'API** : SEC EDGAR est la source de données unique (l'univers des sociétés
cotées, l'ensemble des dépôts, ainsi que les flux fails-to-deliver / suspension
de négociation). Il n'existe **aucune option pour fournir sa propre clé, nulle
part**.

> PennyTune fait ressortir des **éléments probants pour votre propre due
> diligence** - il ne vous dit pas si une action est « saine » ou « un champ de
> mines », ne donne aucun conseil d'achat ou de vente, et ne prédit aucun
> résultat. Il analyse des **sociétés cotées aux États-Unis et enregistrées
> auprès de la SEC** et **ne récupère aucun cours en temps réel** : il ne filtre
> pas selon le cours actuel, ne calcule pas d'indicateurs techniques et n'évalue
> pas la négociabilité (écart bid-ask / liquidité). Vous fournissez le ou les
> tickers à classer, et vous vérifiez vous-même le cours actuel et la
> négociabilité auprès d'un courtier.

---

## ⚠️ Avertissement - à lire attentivement

PennyTune est un outil de recherche et d'éducation, et non un conseil en investissement. Il ne vous dit pas s'il faut acheter, vendre ou conserver un quelconque titre. Les micro-capitalisations et les penny stocks comportent un risque extrême, pouvant aller jusqu'à la perte totale de votre capital. L'avertissement complet, qui constitue la version faisant foi, est disponible en anglais dans le [README en anglais](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) et via la commande `pennytune disclaimer`.

---

## Ce que c'est

Le segment des micro-capitalisations américaines regorge de sociétés qui
paraissent bon marché *pour une raison* - qui brûlent leur trésorerie, qui se
diluent, qui sont proches de la radiation ou qui sont structurées pour la
manipulation. La partie difficile de la due diligence consiste à lire les dépôts
pour repérer ces champs de mines. PennyTune effectue cette lecture pour vous :
pointez-le sur un ticker, ou classez un ensemble organisé de tickers que vous
choisissez, et il extrait les signaux de risque et les indicateurs forensiques
des dépôts SEC de la société - **calculés à partir des dépôts SEC publics de la
société**.

Il fait ressortir des **éléments probants, pas des verdicts.** Il ne vous dit
pas qu'une action est saine ou un champ de mines, ne conseille pas d'acheter ou
de vendre, et ne prédit aucun résultat - le jugement vous appartient.

- **Gratuit et sans clé d'API** - fonctionne entièrement à partir de données
  publiques sans compte ni clé.
- **Enregistrée auprès de la SEC, cotée sur une grande bourse américaine (NYSE/NASDAQ/NYSE American), jamais en OTC** - par construction.
- **Fondé sur des éléments probants** - chaque signal est calculé à partir des
  dépôts SEC publics de la société, et pour les signaux d'alerte liés à des
  événements, l'item 8-K spécifique est nommé.
- **Transparent et ajustable** - un score composite décomposable avec des
  pondérations modifiables par l'utilisateur, des préréglages de filtrage
  (`penny` par défaut / `micro` / `small-cap-value` / `broad` / `custom`), et
  des profils de stratégie sélectionnables (`hold` par défaut / `trader` /
  `high-return` / `custom`).
- **Aucun cours en temps réel** - il ne récupère pas le cours actuel et n'évalue
  pas la négociabilité ; vérifiez-les vous-même auprès d'un courtier.
- **Recherche uniquement, pas un conseil en investissement.**

## Ce qu'il fait ressortir

Pour chaque société, PennyTune lit les dépôts SEC et note les signaux qui
comptent le plus pour une micro-capitalisation - chacun calculé à partir des
dépôts de la société :

- **Santé financière et détresse** - notation de solvabilité Altman Z″, complétée
  d'une batterie forensique (modèles Beneish de manipulation des résultats et
  Piotroski de robustesse) appliquée aux états financiers déposés par la société.
- **Dilution et opérations sur titres** - émissions au titre d'un programme
  d'enregistrement préalable (shelf) et émissions au fil de l'eau (ATM,
  « at-the-market »), hausse du nombre d'actions et vitesse de dilution,
  regroupements d'actions (reverse splits) en série, et indicateurs de
  changement d'auditeur / de retraitement des comptes issus des dépôts 8-K.
- **Activité des initiés** - *achats* d'initiés sur le marché (le signal de
  conviction), tenus distincts des attributions de routine et des retenues
  fiscales afin que les attributions ne soient jamais interprétées comme
  haussières - ainsi que le surplomb (overhang) des ventes proposées au titre du
  Form 144 et l'activité d'actionnariat 13D/13G.
- **Événements importants des 8-K** - le relevé structuré des codes d'item
  (retraitements, changements d'auditeur, départs de dirigeants, manquements aux
  conditions de cotation et autres items importants), pondéré par la gravité
  plutôt que par le simple décompte.
- **Risque d'avis de radiation** - avis divulgués de manquement aux conditions
  de maintien de la cotation (8-K Item 3.01), rapportés sans tenter de deviner le
  décompte de jours du délai lié au cours, que l'outil ne peut pas calculer.
- **Suspensions de négociation actives** - une société faisant l'objet d'une
  suspension de négociation *en cours* de la SEC est signalée et mise à l'écart ;
  les suspensions historiques expirées sont présentées à titre de contexte, sans
  être retenues à l'encontre de la société.
- **Fails-to-deliver** - contexte de tension de règlement issu des données
  bimensuelles fails-to-deliver de la SEC (contexte uniquement - ne constitue pas
  à lui seul une preuve de manipulation).
- **Classification sectorielle** - le secteur SIC de chaque société, afin que les
  comparaisons de qualité et de valorisation soient faites par rapport à des
  pairs de secteur et de taille plutôt qu'à des seuils absolus.

## Données et attribution

PennyTune n'utilise que des données publiques sans clé provenant d'une source
unique : **SEC EDGAR** (l'univers - issu du fichier des sociétés cotées
`company_tickers_exchange.json` de la SEC - ainsi que l'ensemble des dépôts, des
fondamentaux, des formulaires d'initiés et des fichiers fails-to-deliver /
suspension de négociation). La seule identité requise où que ce soit est la
chaîne `User-Agent` de SEC EDGAR (votre nom + e-mail) - un en-tête de requête
que la politique d'accès équitable de la SEC exige pour identifier le demandeur,
et non un compte, un identifiant ou une clé PennyTune. Elle est stockée
uniquement dans votre configuration locale (masquée dans `config get`), envoyée
uniquement dans l'en-tête de requête SEC, et n'est jamais transmise à l'auteur ni
à un quelconque tiers. Tout e-mail personnel valide convient ; la configuration
vérifie le format, pas le fournisseur.

PennyTune est un outil de recherche et ne **republie pas** de jeux de données
bruts de tiers ; votre configuration et tout résultat exporté restent locaux
(jamais versionnés).

## Installation

PennyTune est un outil en ligne de commande publié sur PyPI. Installez-le avec
pip - le choix par défaut, simple et universel :

```bash
pip install pennytune
```

Comme il s'agit d'un outil en ligne de commande, une **installation isolée
(recommandée pour les outils en ligne de commande)** le tient à l'écart de vos
autres environnements Python :

```bash
pipx install pennytune       # isolated install via pipx
uv tool install pennytune    # the same, via uv's tool installer
```

Nécessite Python 3.11-3.14 (tous testés en CI sous Linux, macOS et Windows ;
3.13 est la cible principale pour le linting et la vérification de types).

**Depuis les sources (pour le développement) :**

```bash
git clone https://github.com/lavellehatcherjr/pennytune
cd pennytune
uv sync --extra dev --extra schema   # or: pip install -e ".[dev,schema]"
```

## Utilisation

La configuration initiale enregistre l'identité SEC EDGAR (un en-tête de requête
requis - pas une clé) et la reconnaissance des risques ; `scan`/`inspect`
refusent de s'exécuter tant que les deux n'existent pas :

```bash
pennytune init --identity "Your Name you@example.com" --i-understand-the-risks
```

Le flux de travail principal est **`inspect <TICKER>`** - pointez l'outil sur une
société que vous détenez déjà et obtenez sa ventilation forensique complète
calculée à partir des dépôts :

```bash
# Full evidence-backed breakdown for one ticker (the score, decomposed):
pennytune inspect GROW
pennytune --json inspect GROW | jq '.inspect'   # machine-readable
```

`scan` classe un **ensemble organisé de tickers que vous choisissez** - fournis
explicitement ou lus depuis votre liste de surveillance - selon leurs signaux de
risque issus des dépôts SEC (aucun filtrage par cours - l'outil ne récupère aucun
cours). Au maximum 100 tickers par exécution ; PennyTune ne scanne jamais
l'ensemble du marché. Comme les sous-scores de qualité positifs sont des
percentiles relatifs au secteur/à la taille (significatifs uniquement sur une
large coupe transversale), sur un petit ensemble organisé le classement est
principalement piloté par les signaux de **risque/pénalité** (dilution, détresse,
radiation, ventes d'initiés) - il fait ressortir les noms les plus risqués de
votre ensemble. Ajustez la pondération du risque et la stratégie avec `--preset`
/ `--profile` :

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

Toutes les autres commandes :

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

La sortie commence par un en-tête de fraîcheur (préréglage/profil actif +
horodatages « as-of » par domaine), affiche une bannière d'alerte de liste de
surveillance lorsque c'est pertinent, classe les N premiers, et se termine par le
court avertissement. Les fichiers exportés portent l'en-tête d'avertissement sur
une ligne afin que l'avertissement accompagne les données.

## Développement

```bash
python -m pytest tests/ -v    # run the test suite
ruff check .                  # lint
python -m mypy                # type-check
pip-audit                     # supply-chain scan
```

Les dépendances sont épinglées par hachage dans un fichier `uv.lock` versionné
(discipline de chaîne d'approvisionnement). Les mises à jour sont délibérées et
révisées ; rien n'est fusionné automatiquement.

## Licence

[MIT](https://github.com/lavellehatcherjr/pennytune/blob/main/LICENSE). © Lavelle Hatcher Jr.

---

## ⚠️ Avertissement (répété)

PennyTune est un outil de recherche et d'éducation, et non un conseil en investissement. Il ne vous dit pas s'il faut acheter, vendre ou conserver un quelconque titre. Les micro-capitalisations et les penny stocks comportent un risque extrême, pouvant aller jusqu'à la perte totale de votre capital. L'avertissement complet, qui constitue la version faisant foi, est disponible en anglais dans le [README en anglais](https://github.com/lavellehatcherjr/pennytune/blob/main/README.md) et via la commande `pennytune disclaimer`.
