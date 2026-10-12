# Description des types d'objets de Sinamet

## Généralités et propriétés complémentaires

Les types d'objets présentés dans la suite héritent d'une classe mère `MTObject`.
Chaque MTObject est associée à une liste de propriétés. Certains noms de propriétés sont réservés à des fonctionnalités
spécifiques, par exemple `Code`, `Name`, `Scale`. La liste des propriétés réservées est indiquée pour chaque objet.

En plus de ces propriétés réservées qui ont un sens fonctionnel pour Sinamet,
il est possible d'ajouter d'autres propriétés au nom arbitraire aux objets à travers le mapper.
Par convention, nous conseillons 
d'utiliser des noms de propriétés sans espace, ni caractère spécial ou accentué, par exemple :

    mapper.add("NomDePropriete", "ValeurPropriété")

Les symboles `@` et `#` renvoient à une syntaxe spécifique, permettant de compléter les noms des propriétés.

## Territory

Un "Territoire" (`Territory`) désigne de façon générale une aire géographique (une partie de la surface terrestre) 
généralement désignée par différents acteurs par un nom et/ou un code. Si des limites géographiques peuvent être 
spécifiées, cela n’est pas indispensable tant que l’on ne cherche pas à spatialiser l’information (et on ne cherche 
pas systématiquement à le faire). Il est ainsi possible de conceptualiser des territoires arbitraires,
même si le plus fréquemment il s’agira de faire référence à des territoires largement reconnus, 
notamment ceux formés par le découpage administratif : pays, régions, villes... jusqu’à la parcelle cadastrale
et les bâtiments. En deçà, nous pouvons encore imaginer de diviser les différentes parties d’un bâtiment, 
même si nous ne sommes plus dans le cadre d’un découpage purement géographique mais aussi spatial.

Chaque territoire est associé à des propriétés. En premier, il y a les codes de références qui permettent d’identifier 
des territoires de manière unique dans un référentiel. Il existe une multitude de référentiels : UN M.49, 
ISO-3166 Alpha-2 et Alpha-3, code PNUD, code GAUL, FAOSTAT, AGROVOC et FAOTERM. 
Il existe d’autres identifiants, comme le code Insee en France*, le NUTS utilisé dans l’Union européenne 
ou le FIPS aux États-Unis. Différents services, qu’ils soient publics, communs ou privés, attribuent 
également leurs propres identifiants à des territoires, comme OpenStreetMap, GeoNames, Wikidata, 
des bibliothèques nationales, Facebook, Michelin Voyages, Encyclopædia Britannica Online…

*Le code Insee pose un problème puisqu'il associe un code à deux chiffres aux départements, mais également aux régions. 
Par exemple, le code 44 correspond à la fois à la région Grand Est et au département Loire-Atlantique.
Pour éviter les ambiguïtés, nous faisons habituellement précéder les codes régions par R (RX pour les régions d'avant 2016),
par exemple 'R44' ou 'RX42'.

En plus du code, les territoire ont un voire plusieurs noms (différentes langues, abbréviation, ...). À noter que 
l’usage d’un nom pour identifier un territoire est moins robuste que l’usage du code, en raison des homonymes.

Les territoires ont enfin une longue liste d’attributs possibles, par exemple les countours géographiques ou des données
statistiques (superficie, population, PIB ...).

Les territoires peuvent aussi être liés entre eux par des relations de type frontières communes, 
relation d’inclusion ou succession historique. Dans l’ontologie Sinamet, il n’y a pas de distinction 
entre territoires et groupes de territoires. De ce point de vue, un groupe de territoire est lui-même 
un territoire. Cette approche permet de décrire le monde par une hiérarchie de territoires en évitant 
les problèmes sémantiques liés au regroupement : la France regroupe 18 régions, s’agit-il d’un territoire ou d’un 
groupe de territoires ? Afin d’organiser cette hiérarchie, un attribut d’échelle est associé à chaque territoire 
(par exemple : ville, département, région, pays ...).

### Mots clés réservés, associés aux territoires

- `Code` / `Code@xxx` : Code du territoire (xxx précise le type de code, par exemple 'insee')
- `Name` / `Name@xxx` : Nom du territoire (xxx précise le type de nom, par exemple 'fr', 'en', ...)
- `CodeAlias[@xxx]` / `NameAlias[@xxx]` : Alias de code ou de nom (code ou nom secondaire)
- `Scale` : Echelle du territoire (par exemple 'Region', 'Departement', 'Commune')
- `IsInTerritoryCode[@xxx]` / `IsInTerritoryName[@xxx]` : Code ou nom du territoire parent

## Actor
Un objet "Acteur" (`Actor`) désigne les personnes du territoire qui manipulent des ressources, 
on pourrait à ce titre parler d’agents. Cela peut désigner des personnes morales ou des personnes physiques. 
Pour éviter d’avoir à complexifier l’ontologie, et de manière similaire aux territoires, le terme d’acteur est 
également utilisé pour pouvoir désigner un groupe d’acteur, par exemple un secteur d’activité ou une association.

La caractérisation d’un acteur présente plusieurs similarités avec celle d’un territoire. Ainsi, les acteurs peuvent 
être identifiés par des codes (comme le numéro SIRET, le code RNA), ou par un nom (éventuellement dans différentes
langues). Ils peuvent être caractérisés par de nombreux attributs : adresse ou coordonnées, nombre d’employés 
pour une entreprise, son chiffre d’affaires, son type d’activité… Les acteurs peuvent être liés entre eux (un groupe 
peut posséder plusieurs succursales) ou se succéder. Enfin, ils sont généralement ancrés sur un ou plusieurs 
territoires, par exemple une collectivité qui exerce ses compétences dans ses limites administratives, ou même 
simplement une entreprise implantée sur un terrain.

Les acteurs sont donc associés à différentes propriétés : des attributs d’identification (codes et noms), de 
géolocalisation (adresse, coordonnées), un large panel d’attributs de caractérisation (période d’existence, nombre 
d’employés, chiffre d’affaires…), et des relations avec d’autres acteurs (hiérarchie, succession) et des territoires.

### Mots clés réservés, associés aux acteurs

- `Code` / `Code@xxx` : Code de l'acteur (xxx précise le type de code, par exemple 'siret')
- `Name` / `Name@xxx` : Nom de l'acteur (xxx précise le type de nom, par exemple 'fr', 'en', ...)
- `CodeAlias[@xxx]` / `NameAlias[@xxx]` : Alias de code ou de nom (code ou nom secondaire)
- `Scale` : Echelle / type d'acteur (par exemple : 'GroupeNaf', 'Entreprise', 'Association', ...)
- `IsInTerritoryCode[@xxx]` / `IsInTerritoryName[@xxx]` : Code ou nom du territoire parent
- `IsInActorCode[@xxx]` / `IsInActorName[@xxx]` : Code ou nom de l'acteur parent

## Product
De manière formelle, un "Produit" (`Product`) est l’objet d’un échange entre des acteurs d’un territoire. 
Dans cette définition, ce terme peut ainsi tout aussi bien désigner des objets, la matière qui les compose, 
de l’énergie ou des services. Même si l’étude du métabolisme est avant tout une approche matérielle et énergétique, 
les services contribuent au métabolisme du territoire et peuvent donc être également considérés. Finalement, cette 
définition inclut un large éventail de concepts : du minerai brut, des objets finis, des déchets, de l’électricité, 
des services rendus, le transport de marchandises, des transactions financières, des échanges de données… La librairie 
Sinamet est toutefois plutôt dédiée à l’étude des produits physiques (énergie, matière, mobilité) qui constituent 
directement le métabolisme d’un territoire.

Afin de pouvoir désigner le produit, un nom, qui peut être libre, est nécessaire. Afin de pouvoir classifier 
l’information statistique, le nom du produit doit s’inscrire une nomenclature qui dresse une liste limitée et 
hiérarchisée de possibilités (dans différentes langues), souvent en association avec un code.

Les produits peuvent également être caractérisés par des valeurs physiques ou économiques comme leur durée de vie ou
des coefficients qui vont permettre de changer l’unité de quantification 
(par exemple 1 ordinateur = 8 kg = 1000 € = 300 kg eq. CO2 // 1 kg de fer = 7860 cm3 ...) 
Ils peuvent être également associés à d’autres produits dans d’autres nomenclatures pour permettre la conversion 
de l’une à l’autre, avec éventuellement des coefficients de conversion.

Les produits sont des concepts à minima nommés, régulièrement associés à un code et s’inscrivant fréquemment 
dans une nomenclature pour les hiérarchiser les produits. Les produits peuvent être associés à des caractéristiques 
complémentaires, notamment des coefficients qui permettront le passage entre différentes d’unités, et des références 
vers d’autres produits pour la conversion dans d’autres nomenclatures.

### Mots clés réservés, associés aux produits

- `Code` / `Code@xxx` : Code du produit (xxx précise le type de code)
- `Name` / `Name@xxx` : Nom de produit (xxx précise le type de nom, par exemple 'fr', 'en', ...)
- `CodeAlias[@xxx]` / `NameAlias[@xxx]` : Alias de code ou de nom (code ou nom secondaire)
- `Nomenclature` : Nom de la nomenclature 
- `IsInProductCode` / `IsInProductName[@xxx]` : Code ou nom du produit parent
- `Coefficient@xxx/yyy` : Coefficient de conversion pour le produit (xxx/yyy = rapport d'unité, par exemple kg/m3)

## Stock
Un stock (`Stock`) est défini comme une quantité (dans une ou plusieurs unités) d’un produit appartenant à un acteur et/ou 
localisé sur un territoire à un instant donné. Dans des cas particuliers, le stock peut être défini sur une période,
plutôt qu’à un instant donné, par exemple pour caractériser le temps de transit d’un objet dans une plateforme 
logistique.
Il est possible d’ajouter d’autres attributs à un stock (une référence, sa géolocalisation…). Toutefois, les 
informations sur le produit, la temporalité, la(les) quantité(s) et unité(s), et l’acteur ou le territoire associé 
sont généralement suffisantes pour décrire de manière satisfaisante un stock.

### Mots clés réservés, associés aux stocks

- `TerritoryCode[@xxx]` / `TerritoryName[@xxx]` : Code ou nom du territoire associé au stock
- `ActorCode[@xxx]` / `ActorName[@xxx]` : Code ou nom du territoire associé au stock
- `ProductCode[@xxx]` / `ProductName[@xxx]` : Code ou nom du produit associé au stock
- `ProductNomenclature` : Nomenclature du produit associé au stock
- `Quantity@xxx` : Quantité du stock (xxx désigne l'unité par exemple : 'kg', 'euro', 't', 'unit', ...)
- `DatePoint` : Date du stock

## Gateflow et Pathflow
La notion de flux possède plusieurs définitions selon les disciplines. Trois idées clefs peuvent y être associées :

* Un échange entre deux acteurs (matière, argent ...), éventuellement entre l’environnement et le système socio-économique,
* Un déplacement avec un sens, depuis une origine vers une destination, ainsi qu’éventuellement le chemin correspondant.
* La traversée d’une surface ou d’une frontière (une "porte") par de la matière ou de l’énergie, selon une 
définition plus physique.

Ces idées se recoupent, mais ne sont pas équivalentes, et ne peuvent pas être décrites exactement de la même façon.
Dans tous les cas, définir un flux requiert d’indiquer le produit dont il est constitué, sa quantité (dans une ou
plusieurs unités) et le cadrage temporel du flux (une période ou une date ponctuelle). Il est également nécessaire 
de contextualiser le flux en l’associant au territoire sur lequel il se manifeste, et/ou à l’acteur qui le manipule. 
Ce dernier point amène à devoir distinguer deux types de flux :

* Ceux dont on connaît l’origine (en termes d’acteur et/ou de territoire) ET la destination, et éventuellement le 
chemin. Ils sont appelés "flux de chemin" (`Pathflow`).
* Ceux qui se manifestent à un endroit donné, sans que cela implique de connaître à la fois l’origine et la
destination de manière claire. Ils sont appelés de "flux de porte" (`Gateflow`).

Plusieurs notions courantes du vocabulaire économique et environnemental reposent implicitement sur cette notion : 
lorsqu’on parle d’extraction, de recyclage, de rejets, d’émissions, de production ou de consommation, c’est souvent 
en association avec un seul acteur ou un seul territoire. Les termes "consumption", "production", "emission", "extraction"
sont ainsi disponibles pour classifier l'information et correspondent à des `Gateflow` (voir mapper exemple ci-dessous).
En plus de ces informations minimales, d’autres attributs peuvent compléter la description d’un flux notamment le moyen
de transport (route, rail, eau, air, pipeline, fil électrique ...).

Dans tous les cas, les flux sont associés à un territoire et/ou un acteur (ou deux territoires / deux acteurs pour les
pathflow), à un produit, à une temporalité et à une ou plusieurs quantités (en kg, en euros, ...)

### Mots clés réservés, associés aux Gateflow

- `TerritoryCode[@xxx]` / `TerritoryName[@xxx]` : Code ou nom du territoire associé au stock
- `ActorCode[@xxx]` / `ActorName[@xxx]` : Code ou nom du territoire associé au stock
- `ProductCode[@xxx]` / `ProductName[@xxx]` : Code ou nom du produit associé au stock
- `ProductNomenclature` : Nomenclature du produit associé au stock
- `Quantity@xxx` : Quantité du stock (xxx désigne l'unité par exemple : 'kg', 'euro', 't', 'unit', ...)
- `DatePoint` : Date ponctuelle du flux
- `DateStart` / `DateEnd` : Date de début et de fin du flux
- `Year` / `Month` : Année et moi du flux

### Mots clés réservés, associés aux Pathflow

- `EmitterTerritoryCode[@xxx]` / `EmitterTerritoryName[@xxx]` : Code ou nom du territoire émetteur (origine) du flux
- `EmitterActorCode[@xxx]` / `EmitterActorName[@xxx]` : Code ou nom de l'acteur émetteur (destination) du flux
- `ReceiverTerritoryCode[@xxx]` / `ReceiverTerritoryName[@xxx]` : Code ou nom du territoire receveur (destination) du flux
- `ReceiverActorCode[@xxx]` / `ReceiverActorName[@xxx]` : Code ou nom de l'acteur receveur (destination) du flux
- `ProductCode[@xxx]` / `ProductName[@xxx]` : Code ou nom du produit associé au flux
- `ProductNomenclature` : Nomenclature du produit associé au flux
- `Quantity@xxx` : Quantité du flux (xxx désigne l'unité par exemple : 'kg', 'euro', 't', 'unit', ...)
- `DatePoint` : Date ponctuelle du flux
- `DateStart` / `DateEnd` : Date de début et de fin du flux
- `Year` / `Month` : Année et moi du flux

### Exemple

Exemple du mapper pour le chargement d'un flux de céréales (item 01.1 de la nomenclature NST 2007) entre la Charente
et la Gironde en 2024 (type `Pathflow` car l'origine et la destination sont connus) :
```python
    mapper = Mapper("Pathflow")
    mapper.add("EmitterTerritoryCode@insee", "16")
    mapper.add("ReceiverTerritoryCode@insee", "33")
    mapper.add("ProductCode", "01.1")
    mapper.add("ProductNomenclature", "NST2007")
    mapper.add("Quantity@t", 17)
    mapper.add("Quantity@keuro", 15.6)
    mapper.add("Year", 2024)
```
Exemple du mapper pour la production de céréales en Charente en 2024 
(type `Gateflow` alias `Production` car il n'y a pas d'origine + destination):
```python
    mapper = Mapper("Production")
    mapper.add("TerritoryCode@insee", "16")
    mapper.add("ProductCode", "01.1")
    mapper.add("ProductNomenclature", "NST2007")
    mapper.add("Quantity@t", 17)
    mapper.add("Quantity@keuro", 15.6)
    mapper.add("Year", 2024)
```
