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
- **Déclarants enregistrés auprès de la SEC** - l'univers de tickers provient des
  données publiques de la SEC. Il n'y a aucun filtre par place de cotation : les
  valeurs cotées en OTC sont analysées comme les autres, et le fichier SEC sur
  lequel cela repose ne porte aucune désignation NYSE American.
- **Fondé sur des éléments probants** - les signaux qui sont calculés proviennent
  des dépôts SEC publics de la société, et pour les signaux d'alerte liés à des
  événements, l'item 8-K spécifique est nommé. Deux contributeurs, la valorisation
  et la tonalité de la couverture, n'ont aucune source de données dans cette
  version et sont toujours supprimés (voir **Limites**).
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
comptent le plus pour une micro-capitalisation. Tout signal qu'il ne peut pas
calculer est supprimé et signalé comme tel, jamais noté comme un zéro :

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
- **Événements importants des 8-K** - le relevé structuré des codes d'item,
  pondéré par la gravité plutôt que par le simple décompte. L'Item 4.02, par
  lequel l'émetteur déclare que ses propres états financiers antérieurs ne
  peuvent plus être tenus pour fiables, est nommé et compté séparément de
  l'Item 4.01, un changement d'auditeur, aux côtés des départs de dirigeants,
  des manquements aux conditions de cotation et des autres items importants.
- **Risque d'avis de radiation** - avis divulgués de manquement aux conditions
  de maintien de la cotation (8-K Item 3.01), rapportés sans tenter de deviner le
  décompte de jours du délai lié au cours, que l'outil ne peut pas calculer.
- **Suspensions de négociation** - une société ayant fait l'objet d'une suspension
  de négociation de la SEC au cours des 180 derniers jours est signalée et mise à
  l'écart. Notez que l'outil ne suit pas si la suspension a depuis expiré : les
  suspensions de la SEC durent au plus 10 jours de bourse, une valeur peut donc
  être écartée au titre d'une suspension expirée depuis longtemps.
- **Fails-to-deliver** - contexte de tension de règlement issu des données
  fails-to-deliver publiées deux fois par mois par la SEC (contexte uniquement -
  ne constitue pas à lui seul une preuve de manipulation).
- **Lettres de commentaires de la SEC** - si la Division of Corporation Finance
  a correspondu avec la société au cours de l'année écoulée, combien de lettres
  et de réponses de l'émetteur tombent dans cette fenêtre, et la date de la
  lettre la plus récente. Contexte uniquement, jamais noté. Le registre des
  dépôts consigne la lettre, mais pas son objet.
- **Classification sectorielle** - le secteur SIC de chaque société est enregistré
  et affiché. C'est un contexte uniquement : la notation utilise des bandes de
  référence fixes, et non une comparaison avec des pairs.

## Comment le score fonctionne

Le composite est un **score de recherche pondéré par le risque et non normalisé** :

    composite = somme(pondération x sous-score positif) - somme(pénalité x gravité x confiance)

* Les **contributeurs positifs** sont notés par rapport à des **bandes de
  référence fixes** : l'échelle Piotroski 0-9, les zones de solvabilité Altman Z″,
  et des bandes fixes de VE/chiffre d'affaires et de croissance du chiffre
  d'affaires. Le sous-score d'une société ne dépend donc que de ses propres dépôts,
  et non des autres tickers présents dans l'exécution ; il est comparable d'une
  exécution à l'autre.
* Les **pénalités** se soustraient, mises à l'échelle par la gravité et par le
  préréglage actif.
* **Plus bas signifie que davantage de risque issu des dépôts a été trouvé.** Ce
  n'est pas une valorisation, pas une prédiction, et ce n'est pas comparable à un
  objectif de cours. Un score élevé signifie « moins de risque a été trouvé dans
  les dépôts », jamais « cela va monter ».
* Le score n'est **pas borné** et n'a pas de plage fixe ; traitez-le comme un
  ordre, pas comme une grandeur.

**Un ticker pour lequel aucun élément probant SEC n'a pu être récupéré n'est pas
noté.** Il est signalé comme `NOT ASSESSED`, nommé dans la console, et exclu du
classement, afin que l'absence d'éléments probants ne soit jamais prise pour une
absence de risque.

**La santé financière utilise des seuils réétalonnés, non les bandes publiées
d'Altman.** Altman Z″ est calculé avec ses coefficients publiés, mais les seuils
de solvabilité sont **-3,0 et 1,0**, et non les 1,1 et 2,6 publiés, et le
sous-score est noté en continu plutôt qu'en trois paliers. Mesuré sur 194
déclarants réels, en utilisant la mention de continuité d'exploitation (going
concern) du rapport annuel de chaque société comme étiquette de détresse
indépendante : aux seuils publiés, **aucun des 41 déclarants en continuité
d'exploitation n'a été manqué, mais 47 déclarants sains sur 153 ont été qualifiés
de détresse** - parmi eux Starbucks, HP, AbbVie, Amgen, Oracle, Lowe's, Duke Energy
et AT&T. La limite publiée de 1,1 se situe au 45e centile de la distribution
réelle. Les seuils réétalonnés font passer ce taux de fausse détresse de 31 % à
12 % et ne qualifient toujours aucun déclarant en continuité d'exploitation de
sain. Il s'agit d'un écart délibéré par rapport au modèle publié.

Les exports portent les colonnes `suppressed`, `suppressed_count`,
`evidence_complete` et `completeness`, de sorte qu'une ligne évaluée se distingue
d'une ligne non évaluée sans avoir à lire de texte.

## Limites

Lisez-les avant de faire confiance à un classement.

* **Deux contributeurs sont en permanence à zéro.** `valuation` et `sentiment`
  n'ont aucune source de données dans cette version - il n'y a ni flux de
  capitalisation boursière ni flux d'actualités - ils sont donc supprimés pour
  chaque société, à chaque exécution.
* **Altman n'est pas calculable pour environ un quart des grandes
  capitalisations.** Les banques et les REIT ne publient pas de bilan classé, et
  un certain nombre de grands déclarants ne publient pas de sous-total de résultat
  d'exploitation. Là où il ne peut pas être calculé, il est supprimé et signalé,
  jamais imputé - mais le contributeur « santé financière » manque alors
  entièrement pour cette valeur.
* **La plupart des lignes reposent sur des éléments probants incomplets.** Sur un
  scan représentatif de 20 valeurs, 18 avaient au moins une vérification qui n'a
  pas pu être effectuée. La colonne `suppressed_count` indique combien, par ligne.
* **L'outil classe faiblement, non de façon faisant autorité.** Il est utile pour
  décider quels dépôts lire en premier. Ce n'est pas un filtre sur lequel agir
  directement, et aucun signal isolé ne doit être traité comme un verdict.
* **L'activité de lettres de commentaires est de l'histoire, pas une question
  ouverte.** La SEC ne publie une lettre du personnel qu'au plus tôt 20 jours
  ouvrables après la clôture de l'examen, et le registre des dépôts n'en indique
  pas l'objet. L'outil peut vous dire qu'il y a eu correspondance et quand ; il
  ne peut pas vous dire ce qui a été demandé, ni s'il reste quelque chose en
  suspens. Une lettre sans dépôt de réponse associé n'est pas une lettre restée
  sans réponse : les émetteurs répondent couramment au sein d'un autre dépôt.
* **Une valeur surveillée n'alerte jamais lors de sa première exécution.** Les
  alertes sont calculées par rapport à l'instantané précédent ; une société ne
  déclenche donc rien tant qu'elle n'a pas été analysée au moins deux fois.
* **Pas de cache.** Chaque exécution retélécharge depuis SEC EDGAR. Les réglages
  `cache_ttl` affichés par `config get` sont inertes.

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
l'ensemble du marché. Les sous-scores positifs sont notés par rapport à des
**bandes de référence fixes**, de sorte que le score d'une société ne dépend pas
des autres tickers présents dans l'exécution et reste comparable d'une exécution à
l'autre. Le classement reste néanmoins principalement piloté par les signaux de
**risque/pénalité** (dilution, détresse, radiation, ventes d'initiés), puisque ce
sont ceux que les dépôts étayent le mieux. Ajustez la pondération et la stratégie
avec `--preset` / `--profile` :

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
pennytune watch list          #   run-over-run score deltas
pennytune config get          # view all settings (EDGAR email redacted)
pennytune config set weights.valuation 1.5   # tune a scoring weight
pennytune config set profile custom          # switch to hand-tuned weights
pennytune sources             # data sources, rate limits, contacted domains
```

La sortie de `scan` commence par un en-tête (préréglage/profil actif + lignes de
fraîcheur des données), classe les N premiers, et se termine par le court
avertissement. Les fichiers exportés portent l'en-tête d'avertissement sur une
ligne afin que l'avertissement accompagne les données.

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
