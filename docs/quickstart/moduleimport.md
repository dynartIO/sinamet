# Importation en lot les données de prise en main

Afin de simplifier la prise en main, un package de données et de fichiers d'importations
est disponible pour la [suite du tutoriel](requesting.md).

Télécharger et extraire les données et modules suivants
dans un dossier spécifique (que nous appellerons `dossier_modules`) : 
[https://docs.sinamet.tech/static/demo_sinamet.zip](https://docs.sinamet.tech/static/demo_sinamet.zip)

Ce package permet l'injection des données suivantes :

* **Package `demo_territory_france`**
    * Des pays du monde
    * Des régions françaises (avant 2015 et actuelles)
    * Des départements français
    * De la population des départements entre 1990 et 2023
* **Package `nomenclature_nst2007`**
    * Nomenclature pour les Statistiques de transport
* **Package `demo_sitram`**
    * Les statistiques sur le transport de marchandises entre départements entre 
2015 et 2018
* **Package `demo_immatriculation_vehicules`**
    * Une nomenclature des véhicules particuliers
    * Les immatriculations des voitures particulières neuves par département entre
2010 et 2019
* **Package `demo_script`**
    * Reprend les lignes de code de la page [Requêter les données](requesting.md)

Avant de charger les données, il est nécessaire de réinitialiser la base de données.
Pour cela, il suffit d'exécuter les lignes suivantes :

```python
from sinamet import Sidb
with Sidb.connect() as sidb:
    sidb.reset()
```

Ensuite, pour charger les données, il suffit d'exécuter les scripts suivants dans l'ordre :
    
    demo_territory_france/cmd_imp_0_pays.py
    demo_territory_france/cmd_imp_1_regions.py
    demo_territory_france/cmd_imp_2_departements.py
    demo_territory_france/cmd_imp_2b_departements_population.py
    nomenclature_nst2007/cmd_imp_nomenclature_nst2007.py
    demo_sitram/cmd_imp_sitram_route_vnf.py *
    demo_sitram/cmd_imp_sitram_international_route_vn.py
    demo_immatriculation_vehicules/cmd_imp_nomenclature_voitures.py
    demo_immatriculation_vehicules/cmd_imp_voitures.py


\* *Ce fichier peut être particulièrement long à exécuter selon performances de l'ordinateur : ~ 10 min*

L'objectif de Sinamet est de permettre la mise en cohérence de différents jeux de données de provenances multiples.
Certains jeux de données peuvent être dépendants d'autres, par exemple les départements nécessitent 
que les régions soient importées et les flux nécessitent que les départements et la nomenclature soient importés. 
D'où l'importance d'exécuter ces modules dans l'ordre.

Ensuite, les imports sont décomposés pour avoir un fichier par source de données. Ça n'a rien d'obligatoire, mais ça 
permet de rendre modulaire l'information. On peut ainsi réutiliser des briques d'un projet à l'autre. 


## Quelques explications

Sinamet est conçu pour faciliter le partage des algorithmes de traitements, aussi bien pour l'importation des données,
que pour leur exportation et analyse. Les différents modules ci-dessus, accompagnés des données brutes, permettent
ainsi de charger rapidement des données nettoyées et structurées, sans avoir à construire soi-même les modules
d'importation. Evidemment, il est tout à fait possible de construire ses propres modules d'importation, 
en chargeant des [Mapper](../documentation/mapper.md) comme cela est expliqué ci-dessous.
L'utilisateur est toutefois dispensé de ce travail créatif dans ce tutoriel de prise en main.

Pour comprendre la logique derrière les modules d'importation, prenons par exemple le module 
`demo_territory_france/cmd_imp_0_pays.py`, dont l'objet est d'importer les pays du monde.
La source de données est fournie (cf dossier data), elle provient de "The World Bank Group", avec un post-traitement
pour simplifier les géométries de frontières. Le module d'importation créé d'abord le monde entier comme un territoire.
On lui donne un code, un nom en français et en anglais, et une échelle, pour pouvoir structurer la base.

```python
  mapper = Mapper("Territory", source_ref=mysrcref)
  mapper.add("Code", "WORLD", primarykey=True)
  mapper.add("Name@fr", "Monde")
  mapper.add("Name@en", "World")
  mapper.add("Scale", "World")
  sidb.load(mapper)
```

On ajoute également "Autres pays" comme un territoire, qui est un peu un territoire "fourre-tout pour le reste",
certains jeux de données y faisant référence après une liste de pays.

Ensuite, nous itérons sur le fichier de données pour créer les différents pays en base. Pour une meilleure compréhension
le code ci-dessous est simplifié (les tests conditionnels du fichier original servent à nettoyer certaines données avant
leur importation) :

```python
for row in df.to_dict(orient='records'):
    mapper = Mapper('Territory', source_ref=mysrcref)
    mapper.add("Code@isoa2", row["FIPS_10_"], primarykey=True)
    mapper.add("Code@isoa3", row['ISO_A3'])
    mapper.add("Name@fr", row['NAME_FR'])
    mapper.add("Name@en", row['NAME_EN'])
    mapper.add("Name@de", row['NAME_DE'])
    mapper.add("IsInTerritoryCode", "WORLD")
    mapper.add("Scale", "Country")
    mapper.add("Shape", row['geometry'])
    sidb.load(mapper)
```

Pour chaque ligne du fichier de données, nous créons un mapper de type "Territory" (donc servant à créer ou mettre
à jour un territoire), puis nous ajoutons les différentes
propriétés : des codes (isoa2 pour ISO 3166-1 alpha-2, isoa3 pour ISO 3166-1 alpha-3), les noms (en français, en anglais,
en Allemand), l'échelle (Scale = 'Country'), les limites géographiques (Geoshape). Notons en particulier la prorpriété
`IsInTerritoryCode` qui désigne le territoire parent par son code (nous pourrions aussi utiliser *IsInTerritoryName*).
Cette propriété est spécifique car elle permet d'organiser la hiérarchie des territoires, que nous pourrons ainsi
interroger par la suite.

Ensuite, les fichiers `cmd_imp_1_regions.py`, `cmd_imp_2_departements.py`, `cmd_imp_2b_departements_population.py`
servent à importer les régions (anciennes et nouvelles) et départements français, en précisant le nom et le code insee
(précédé de R pour les nouvelles régions et RX pour les anciennes), ainsi que la hiérarchie territoriale.

Le fichier `nomenclature_nst2007/cmd_imp_nomenclature_nst2007.py` sert quand à lui à l'importation des produits de la
nomenclature NST2007 utilisée pour structurer les données sur les statistiques de transport de marchandises (Sitram).

```python
  mapper = Mapper("Product", source_ref=mysrcref)
  mapper.add("Nomenclature", "NST2007")
  mapper.add("Name@fr", row['Intitulé'])
  mapper.add("Code", str(row['Code']), primarykey=True)
  mapper.add("CodeAlias", str(row['Code']).replace(".",""))
  mapper.add("IsInProductCode", _____)
  sidb.load(mapper)
  sidb.progress()
```

Comme nous le voyons, nous précisons la propriété "Nomenclature" pour les produits, nous ajoutons ici un alias de code
(qui permet la recherche par cet alias, mais n'est pas considéré comme référence standard), et *IsInProductCode*
qui permet d'organiser la hiérarchie des produits dans la nomenclature. `sidb.progress()` permet de suivre
la progression du chargement des données.

Une fois les départements et les produits de la nomenclature NST2007 importés, il devient possible de charger
les données Sitram. Ces données décrivent des flux entre différents départements :

```python
  mapper = Mapper("Pathflow", source_ref=mysrcref)
  mapper.add("EmitterTerritoryCode@insee", row['département de chargement'])
  mapper.add("ReceiverTerritoryCode@insee", row['département de déchargement'])
  mapper.add("Year", year)
  mapper.add("ProductCode", row['Position'])
  mapper.add("ProductNomenclature", "NST2007")
  mapper.add("Quantity@t", row['Tonnes redressées'])
  mapper.add("Quantity@t.km", row['tonnes * kilomètres redressées'])
  mapper.add("Quantity@nbobs", row["Nombre d'observations"])
  mapper.add("TransportMean", row["L mode de transport"]) # Route ou Voie navigable
  sidb.load(mapper)
  sidb.progress()
```

Ici, nous indiquons pour chaque flux l'origine (EmitterTerritory) et la destination (ReceiverTerritory), la période
concernée (Year), le produit (ProductCode + ProductNomenclature), le moyen de transport (TransportMean) et la quantité
dans différentes unités (t, t.km, nbobs - nombre d'observations).

Pour les fichiers suivants (immatriculation des véhicules), la logique est la même : on importe la nomenclature adaptée
avec `cmd_imp_nomenclature_voitures.py`, puis les statistiques associées avec `cmd_imp_voitures.py`.

Dans la section suivante sur les [requêtes de données](requesting.md), nous allons voir
comment requêter les données chargées.
