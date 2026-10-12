# Requêter les données

Une fois que les [données de démo sont chargées](../quickstart/moduleimport.md), il devient possible de 
les requêter facilement (c'est tout l'objet de la librairie).


## Requête sur des territoires

Il convient tout d'abord de récupérer ces territoires en tant qu'objet depuis la base de données.
Notez que toutes les opérations d'extraction et d'analyse doivent prendre place dans un bloc uni
défini par `with Sidb.connect() as sidb` (les objets ne sont pas persistants d'un bloc à l'autre).
```py linenums='1'
from sinamet import Sidb

with Sidb.connect() as sidb:
    charente = sidb.get_territory(code_insee="16")
    nouvelleaquitaine = sidb.get_territory(name="Nouvelle-Aquitaine")
    print("Territoire requêté:", charente)
    print("Territoire requêté:", nouvelleaquitaine)
```

Résultat:
``` { .text .no-copy }
Territoire requêté: <Territory-312: 16-Charente>
Territoire requêté: <Territory-265: R75-Nouvelle-Aquitaine>
```
Si nécessaire, il est possible d'afficher uniquement le
[code](../documentation/mtobject.md#mtobjects.mtobject.MTObject.get_code) ou le
[nom](../documentation/mtobject.md#mtobjects.mtobject.MTObject.get_name)
d'un territoire, plutôt que la chaîne-objet:
```py linenums='9'
    print(charente.get_name(), charente.get_code('insee'))
    print(nouvelleaquitaine.get_name(), nouvelleaquitaine.get_code())
```
Résultat:
``` { .text .no-copy }
Nouvelle-Aquitaine R75
Charente 16
```

Note : Certains objets (territoires, acteurs, produits) peuvent avoir plusieurs codes et/ou noms, 
il est possible de préciser le type de code ou de nom pour éviter les ambiguités, 
par exemple `charente.get_code('insee')`. Il existe aussi les methodes
[`get_codes()`](../documentation/mtobject.md#mtobjects.mtobject.MTObject.get_codes) et
[`get_names()`](../documentation/mtobject.md#mtobjects.mtobject.MTObject.get_names)
qui peuvent être utilisées pour traiter des codes et noms multiples.

Comme nous avons chargé les données de population pour les départements, 
nous pouvons aussi les récupérer facilement à travers la méthode `get_property()`.

```py linenums='12'
    population_charente_2023 = charente.get_property("Population", date_point="01/01/2023")
    print(f"La population de {charente.get_name()} en 2023 est de {population_charente_2023} habitants")
```

Résultat:
``` { .text .no-copy }
La population de Charente en 2023 est de 351036.0 habitants
```

Nous avons également chargé la hiérarchie des territoires, il est ainsi possible de récupérer tous les territoires
d'une échelle donnée.

```py linenums='15'
    lst_dep = sidb.get_territories_in(nouvelleaquitaine, scale="Departement")
    print("Départements de Nouvelle Aquitaine:", [f"{dep.get_name()} ({dep.get_code('insee')})" for dep in lst_dep])
```

Résultat:

``` { .text .no-copy }
Départements de Nouvelle Aquitaine: ['Charente (16)', 'Charente-Maritime (17)',
'Corrèze (19)', 'Creuse (23)', 'Dordogne (24)', 'Gironde (33)', 'Landes (40)',
'Lot-et-Garonne (47)', 'Pyrénées-Atlantiques (64)', 'Deux-Sèvres (79)',
'Vienne (86)', 'Haute-Vienne (87)']
```

## Requete sur des flux de type Pathflow

Maintenant que nous avons chargé nos territoires depuis le script, il est possible d'aller interroger
les données sur le transport de marchandises entre différents territoires. 

Au préalable, nous devons aussi choisir le produit concerné selon la nomenclature NST2007 qui définit
la classification statistique des données Sitram. Vous pouvez consulter cette nomenclature
dans le dossier `modules/nomenclature_nst2007/data`. Nous prendrons pour l'exemple l'item `01.1 - Céréales`.

```py linenums='18'
    mon_produit = sidb.get_product(code='01.1', nomenclature='NST2007')
    print("Mon produit:", mon_produit)
```

Résultat:
``` { .text .no-copy }
Mon produit: <Product-422:NST2007(01.1)-Céréales>
```

Les données sur le transport de marchandises sont stockées comme des
[Pathflows](../documentation/mtobjecttypes.md), avec un territoire
d'origine et de destination. Pour récuperer les pathflows, nous disposons des fonctions
[`sidb.get_imports()`](../documentation/sidb.md#sidb.Sidb.get_imports),
[`sidb.get_exports()`](../documentation/sidb.md#sidb.Sidb.get_exports) et
[`sidb.get_internals()`](../documentation/sidb.md#sidb.Sidb.get_internals).

```py linenums='21'
    flux_import = sidb.get_imports(charente, product=mon_produit)
    print(f"{len(flux_import)} flux de {mon_produit.get_name()} à destination de {charente.get_name()} ont été requêtés")
```

Résultat:
``` { .text .no-copy }
83 flux de Céréales à destination de Charente ont été requêtés.
```

Comme les données sur les flux sont exprimés en tonnes (t), il est possible de calculer la masse de ces flux.
Il faut au préalable importer l'outil Profile `from sinamet.tools.profile import Profile`.

```py linenums='24'
    annee = 2017
    quantite = Profile.get_value(flux_import, "t", year=annee)
    print(f"Soit {quantite} t en {annee}")
```

Résultat:
``` { .text .no-copy }
Soit 50582.0 t en 2017
```

Note : on pourrait demander à avoir les valeurs en kilotonnes, plutôt qu'en tonnes, 
il suffit de remplacer l'unité dans l'option profil. 
Sinamet se charge de la conversion des unités (voir [Convertisseur d'unité](../documentation/tools.md))

```py linenums='28'
    quantite = Profile.get_value(flux_import, "kt", year=annee)
    print(f"Soit {quantite} kt en {annee}")
```

Résultat:
``` { .text .no-copy }
Soit 50.582 kt en 2017
```

Sinamet intègre différentes fonctionnalités qui permettent de requêter les données en fonction des territoires.
Ainsi, si les données initiales décrivent des flux entre départements, la hiérarchie territoriale définie
par les données importées permettent de travailler également à l'échelle des régions.

```py linenums='31'
    bretagne = sidb.get_territory(code='R53')  # Région 53 = Bretagne
    flux_import = sidb.get_imports(bretagne, product=mon_produit)
    quantite = Profile.get_value(flux_import, "kt", year=annee)
    print(f"{quantite} kt de {mon_produit.get_name()} importé par {bretagne.get_name()} en {annee}")
```

Résultat:
``` { .text .no-copy }
1359.6930000000002 kt de Céréales importé par Bretagne en 2017.
```

De manière plus avancées, il est possible de filtrer les données en fonction des origine et destination,
à l'aide du paramètre `related_target`, 
par exemple tous les flux de céréales en provenance de Charente et à distination de Bretagne :

```py linenums='36'
    flux_export = sidb.get_exports(charente, related_target=bretagne, product=mon_produit)
    print(f"{len(flux_export)} flux en provenance de {charente.get_name()} et à destination de {bretagne.get_name()} ont été requêtés")
```

Résultat:
``` { .text .no-copy }
23 flux en provenance de Charente et à destination de Bretagne ont été requêtés.
```

De la même manière, il est possible d'exclure les flux en provenance ou destination d'un territoire spécifique,
à l'aide du paramètre `exclude_related_target`.

## Requete sur des flux de type Gateflow

Les exemples précédents s'appuyait sur les données de statistiques de transport de marchandises qui se décrivent
comme des Pathflow. Dans cette section, nous examinons les statistiques sur l'immatriculation des voitures 
particulières neuves. Ces données sont structurées comme des Gateflow de consommation, car les données ne mentionnent
pas une origine et destination.

De manière similaire, il faut déjà requêter les territoires et le produit concerné.

```py linenums='39'
with Sidb.connect() as sidb:
    charente = sidb.get_territory(code_insee='16')
    voiture_elec = sidb.get_product(name='Electricité', nomenclature='Voitures')
```

Il n'y a plus qu'à requêter les données. L'unité de quantification ici est l'unité (unit) :

```py linenums='43'
    vehicules = sidb.get_consumptions(charente, product=voiture_elec)
    annee = 2018
    quantite = Profile.get_value(vehicules, 'unit', year=annee)
    print(f"{quantite} voitures {voiture_elec} neuves particulières immatriculées "
          f"en {charente.get_name()} en {annee}.")
```

Résultat:
``` { .text .no-copy }
158.0 voitures <Product-593177:Voitures(###)-Electricité> neuves particulières immatriculées en Charente en 2018.
```

## Travailler avec la session SQLAlchemy

Sinamet s'appuie sur l'ORM (Object-Relational Mapping) SQLAlchemy pour permettre la manipulation de la base de données 
à travers des objets de données. Les fonctions présentées précédemment permette de construire facilement des requêtes
sur les données de flux et de stocks, mais il est possible de construire une requête personnalisée à partir de l'[objet
session de SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session.html), disponible via `sidb.session`, par exemple:

```py linenums='1'
from sqlalchemy import select
from sinamet import Sidb
from sinamet.mtobjects import Territory

with Sidb.connect() as sidb:
    mystatement = select(Territory)
    res = sidb.session.execute(mystatement).all()
    print(f"{len(res)} territoires dans la base de données")
```

Résultat:
``` { .text .no-copy }
400 territoires dans la base de données
```
