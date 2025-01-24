# Premier modèle

Avant de commencer ce premier exercice de prise en main, assurez-vous qu'une base de données PostgreSQL/PostGIS 
est montée et accessible, 
et que le fichier de configuration `sinamet_config.toml` est correctement paramétré en conséquence 
(voir [Installation](../installation.md)).


## Description du cas d'étude

Afin de disposer d'un cas simple pour ce premier exercice de prise en main, nous proposons l'exercice suivant :

Nous étudions les flux de choux et de carottes entre 3 départements : 
Le Bas-Rhin (67), le Haut-Rhin (68) et les Vosges (88).

Les données (fictives) décrivant ces flux sont : 

- La production de choux en 2023 (respectivement de carottes) dans ces 
départements est de 35000 t (2300 t) dans le Bas-Rhin, 28000 t (5700 t) dans le Haut-Rhin, 
et 1700 t (6800 t) dans les Vosges.
- Les flux transportés entre différents départements sont présentés dans le tableau suivant : 

| Origine     | Destination | Produit  | Quantité (en t) |
|:------------|:------------|:---------|----------------:|
| Bas-Rhin    | Haut-Rhin   | Choux    |            1300 |
| Bas-Rhin    | Vosges      | Choux    |            2800 |
| Vosges      | Haut-Rhin   | Carottes |             750 |
| Vosges      | Bas-Rhin    | Carottes |            1200 |
| Haut-Rhin   | Bas-Rhin    | Carottes |            1700 |
| Haut-Rhin   | Vosges      | Choux    |            2400 |

## Importation

Pour ce tutoriel, nous aurons besoin d'importer les classes suivantes :

```python
from sinamet import Sidb, Mapper
from sinamet.tools.profile import Profile
```

## Initialisation de la base de données

Afin de disposer d'une base de données vierge de toutes données, nous commençons notre script par une réinitialisation. 
Cela est conseillé ici pour suivre ce premier exemple pas à pas et pouvoir relancer le script plusieurs fois en repartant
de 0, mais dans la pratique, c'est une fonction très rarement appelée parce qu'elle vide entièrement la base de données,
alors que Sinamet a au contraire pour objectif de la construire à travers les fonctionnalités d'importation.

```python
with Sidb.connect() as sidb:
    sidb.reset()
```

De manière générale, toutes les interactions avec la base de données doivent prendre place dans un bloc 
défini par `with Sidb.connect() as sidb`. Sidb est l'accronyme de *Sinamet Interface DataBase*.


## Créer le modèle Territoire-Acteur-Produit

La première étape pour la structuration des données de flux est de construire le modèle Territoire-Acteur-Produit.
Dans cet exemple simple, il n'y a pas d'acteur, seulement des territoires et des produits.

La création des objets dans la base se fait par l'intermédiaire de la classe [`Mapper`](../documentation/mapper.md). 
Ces `Mapper`, lorsqu'ils sont chargés, permettent de créer des objets (s’ils n’existent pas déjà) 
et d’y associer des propriétés (attributs ou relations) à travers des mots-clés. 


### Modèle territorial

Pour créer les 3 territoires, nous devons créer 3 [`Mapper`](../documentation/mapper.md) et les charger.
Pour les territoires, il est nécessaire de préciser une échelle, ici "Departement". 

Dans le script ci-dessous, la fonction `sidb.load(mapper)` charge le `Mapper` vers la base de données : 
elle va créer ou mettre à jour dans la base les objets définis par ce `Mapper`.

Sinamet définit des mots-clés spécifiques comme `Code`, `Name`, `Scale` qui sont réservés dans le modèle de données.
L'ensemble des mots clés réservés est présenté dans la page sur les [types d'objets de Sinamet](../documentation/mtobjecttypes.md).

```python
with Sidb.connect() as sidb:
    mapper = Mapper("Territory")
    mapper.add("Code", "67")
    mapper.add("Name", "Bas-Rhin")
    mapper.add("Scale", "Departement")
    sidb.load(mapper) 

    mapper = Mapper("Territory")
    mapper.add("Code", "68")
    mapper.add("Name", "Haut-Rhin")
    mapper.add("Scale", "Departement")
    sidb.load(mapper) 

    mapper = Mapper("Territory")
    mapper.add("Code", "88")
    mapper.add("Name", "Vosges")
    mapper.add("Scale", "Departement")
    sidb.load(mapper) 
```

Si vous exécutez le script précédent, vous aurez un avertissement indiquant que la source de données n'est pas
renseignée. Nous abordons cette question de la source de données en [appronfondissement](indepth.md), il n'est pas bloquant.

Nous voulons aussi ajouter l'ancienne région "Alsace" (ancien code régional Insee : 42) à notre modèle territorial.

```python
with Sidb.connect() as sidb:
    mapper = Mapper("Territory")
    mapper.add("Code", "RX42")
    mapper.add("Name", "Alsace")
    mapper.add("Scale", "RegionX")
    sidb.load(mapper) 
```
    
Note : l'ajout de RX devant le code Insee régional permet d'éviter les ambiguités entre code départements, et code
d'anciennes régions.

Pour faire le lien entre la région Alsace et ses départements, nous devons de nouveau mapper les départements, avec
le mot-clé réservé `IsInTerritoryCode`:

```python
with Sidb.connect() as sidb:
    mapper = Mapper("Territory")
    mapper.add("Code", "67")
    mapper.add("IsInTerritoryCode", "RX42")
    sidb.load(mapper)  

    mapper = Mapper("Territory")
    mapper.add("Code", "68")
    mapper.add("IsInTerritoryCode", "RX42")
    sidb.load(mapper)  
```

Il est important de souligner que les mots clés `Code` et `Name` servent de clé de recherche par défaut. Ainsi,
lors du chargement d'un [`Mapper`](../documentation/mapper.md) vers la base de données, ces propriétés sont utilisées pour vérifier si un objet
avec ce code ou nom existe déjà dans la base de données. Si oui, l'objet existant est mis à jour avec les 
propriétés supplémentaires (c'est le cas sur les deux derniers [`Mapper`](../documentation/mapper.md)), 
si non un nouvel objet est créé. Voir [cette section pour en savoir plus sur les clés primaires et étrangères](indepth.md).

Il est souvent plus logique de commencer par les territoires les plus grands, puis d'ajouter
les territoires plus petits. Cela permet de ne créer qu'un seul [`Mapper`](../documentation/mapper.md) au lieu 
de deux (un premier pour charger les infos de bases, puis un second pour définir la hiérarchie des territoires).

Une fois l'ensemble des mappers chargés, il est possible de requêter les objets dans la base. Par exemple :

```python
with Sidb.connect() as sidb:
    alsace = sidb.get_territory(code = "RX42")
    print(alsace)
    deps = sidb.get_territories_in(alsace, scale="Departement") # Récupères les départements d'Alsace
    print([dep.get_name() for dep in deps])
```
        
affichera :

    <Territory-4: RX42-Alsace>
    ['Bas-Rhin', 'Haut-Rhin']

### Importer la nomenclature des produits

Une fois les territoires créés dans la base, nous pouvons ensuite créer les produits.
Les produits doivent être organisés dans des nomenclatures. Ici, notre nomenclature s'appelera "Aliments".
Nous créons les choux et les carottes, ainsi qu'une catégorie de regroupement "Légumes".

```python
with Sidb.connect() as sidb:
    mapper = Mapper("Product")
    mapper.add("Name", "Légumes")  
    mapper.add("Nomenclature", "Aliments")
    sidb.load(mapper)  

    mapper = Mapper("Product")
    mapper.add("Name", "Choux")
    mapper.add("IsInProductName", "Légumes")  
    mapper.add("Nomenclature", "Aliments")
    sidb.load(mapper)  

    mapper = Mapper("Product")
    mapper.add("Name", "Carottes") 
    mapper.add("IsInProductName", "Légumes")  
    mapper.add("Nomenclature", "Aliments")
    sidb.load(mapper)  
```

Notons les mots clés réservés : `Name`, `IsInProductName`, `Nomenclature`.


## Importer les flux

Une fois le modèle Territoires-Acteurs-Produits importé, il est possible d'importer les flux de choux et de carottes.

### Production

Commençons par la production. Les mappers de production sont :

```python
with Sidb.connect() as sidb:
    mapper = Mapper("Production")
    mapper.add("TerritoryCode", "67")  
    mapper.add("ProductName", "Choux")  
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 35000)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Production")
    mapper.add("TerritoryCode", "68")  
    mapper.add("ProductName", "Choux")  
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 28000)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Production")
    mapper.add("TerritoryCode", "88")  
    mapper.add("ProductName", "Choux")  
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 1700)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Production")
    mapper.add("TerritoryCode", "67")  
    mapper.add("ProductName", "Carottes")  
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 2300)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Production")
    mapper.add("TerritoryCode", "68")  
    mapper.add("ProductName", "Carottes")  
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 5700)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Production")
    mapper.add("TerritoryCode", "88")  
    mapper.add("ProductName", "Carottes")  
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 6800)
    mapper.add("Year", 2023)
    sidb.load(mapper)  
```

Notons les mots clés réservés : `TerritoryCode`, `ProductName`, `ProductNomenclature`, `Quantity`, `Year`. L'unité de
`Quantity` est précisée grâce au suffixe @ : `Quantity@t`.

Une fois ces données chargées, il est possible de les requêter facilement, par exemple :

```python
with Sidb.connect() as sidb:
    territoire = sidb.get_territory(code='88')
    produit = sidb.get_product(name='Choux', nomenclature="Aliments")
    flux_production = sidb.get_productions(territoire, product=produit)
    print(f"{len(flux_production)} flux de {produit.get_name()} produits dans "
          f"{territoire.get_name()} ont été requêtés.")
    annee = 2023
    quantite = Profile.get_value(flux_production, "t", year=annee) # Obtenir la valeur en tonne de tous les flux
    print(f"soit {quantite} tonnes")
```
        
affichera :

    1 flux de Choux produits dans Vosges ont été requêtés.
    soit 1700.0 tonnes

Un des intérêts de Sinamet va être de réaliser automatiquement les aggrégations territoriales et de nomenclature.
Ainsi, grâce au modèle territorial et à la nomenclature définis précédemment, il est possible de requêter les
productions de Légumes en Alsace, ce qui retournera les productions de choux et de carottes du Bas-Rhin et du Haut-Rhin :

```python
with Sidb.connect() as sidb:
    territoire = sidb.get_territory(name='Alsace')
    produit = sidb.get_product(name='Légumes', nomenclature="Aliments")
    flux_production = sidb.get_productions(territoire, product=produit)
    print(f"{len(flux_production)} flux de {produit.get_name()} produits dans "
          f"{territoire.get_name()} ont été requêtés.")
    annee = 2023
    quantite = Profile.get_value(flux_production, "t", year=annee) # Obtenir la valeur en tonne de tous les flux
    print(f"soit {quantite} tonnes")
```

affichera:

    4 flux de Légumes produits dans Alsace ont été requêtés.
    soit 71000.0 tonnes


### Flux entre départements

Les flux dont on connaît l'origine et la destination sont appelés `Pathflow` dans le modèle de données Sinamet.
Pour ajouter les données présentées précédemment, on définit les mappers adaptés :

```python
with Sidb.connect() as sidb:
     mapper = Mapper("Pathflow")
    mapper.add("EmitterTerritoryCode", "67")
    mapper.add("ReceiverTerritoryCode", "68")
    mapper.add("ProductName", "Choux")
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 1300)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Pathflow")
    mapper.add("EmitterTerritoryCode", "67")
    mapper.add("ReceiverTerritoryCode", "88")
    mapper.add("ProductName", "Choux")
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 2800)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Pathflow")
    mapper.add("EmitterTerritoryCode", "88")
    mapper.add("ReceiverTerritoryCode", "68")
    mapper.add("ProductName", "Carottes")
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 750)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Pathflow")
    mapper.add("EmitterTerritoryCode", "88")
    mapper.add("ReceiverTerritoryCode", "67")
    mapper.add("ProductName", "Carottes")
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 1200)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Pathflow")
    mapper.add("EmitterTerritoryCode", "67")
    mapper.add("ReceiverTerritoryCode", "68")
    mapper.add("ProductName", "Carottes")
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 1700)
    mapper.add("Year", 2023)
    sidb.load(mapper)  

    mapper = Mapper("Pathflow")
    mapper.add("EmitterTerritoryCode", "68")
    mapper.add("ReceiverTerritoryCode", "88")
    mapper.add("ProductName", "Choux")
    mapper.add("ProductNomenclature", "Aliments")
    mapper.add("Quantity@t", 2400)
    mapper.add("Year", 2023)
    sidb.load(mapper)  
```

Les pathflows sont requêtés par les fonction get_exports(), get_imports() et get_internals(). Le modèle territorial
permet de travailler à des échelles supérieures.

Exemple :

```python
from sinamet.tools.profile import Profile
with Sidb.connect() as sidb:
    territoire = sidb.get_territory(code='67')
    produit = sidb.get_product(name='Choux', nomenclature="Aliments")
    flux_export = sidb.get_exports(territoire, product=produit)
    print(f"{len(flux_export)} flux de {produit.get_name()} exportés par "
          f"{territoire.get_name()} ont été requêtés.")
    annee = 2023
    quantite = Profile.get_value(flux_export, "t", year=annee) # Obtenir la valeur en tonne de tous les flux
    print(f"soit {quantite} tonnes")

with Sidb.connect() as sidb:
    territoire = sidb.get_territory(name='Alsace')
    produit = sidb.get_product(name='Légumes', nomenclature="Aliments")
    flux_imports = sidb.get_exports(territoire, product=produit)
    print(f"{len(flux_imports)} flux de {produit.get_name()} importés par "
          f"{territoire.get_name()} ont été requêtés.")
    annee = 2023
    quantite = Profile.get_value(flux_imports, "t", year=annee) # Obtenir la valeur en tonne de tous les flux
    print(f"soit {quantite} tonnes")
```





## Suite du tutoriel

Dans cette section, nous avons présenté comment créer quelques objets d'études dans la base de données (des territoires,
des produits, des flux), et comment les requêter.

La création "Mapper par Mapper" est un peu lourde lorsqu'il s'agit le faire manuellement. En pratique, les données
sont souvent disponibles dans un tableur. Dans ce cas, les mappers sont construits en itérant sur les lignes de
données. La section suivante permet l'[import en masse de données](moduleimport.md) : les modules d'importation
sont prêt à l'emploi, et ne nécessite pas de reconstruire les Mapper.



