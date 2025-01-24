# Tutoriel

Sinamet est spécialisé pour la structuration de données décrivant des flux territorialisés. Ces flux peuvent être de 
toutes sortes (Energie, Matière, Mobilités, Monétaire, ...), c'est à l'utilisateur de définir les nomenclatures des
produits qu'il souhaite étudier.

Afin de comprendre le fonctionnement de Sinamet, il faut détailler quelques éléments conceptuels : 
la séquentialité des traitements (importation puis requêtage), les types d'objets manipulés,
et la base de données en lien avec un ORM.


## Séquentialité des traitements
La librairie Sinamet s’utilise en 2 temps :

* D'abord l’importation de données externes dans la base de données centralisée gérée par Sinamet. 
* Ensuite le requêtage et la manipulation des données pour produire les analyses et visualisations.


## Types d'objets et propriétés

Sinamet est utilisé pour structurer de la donnée portant sur la description de flux territorialisés. Cette information
s'articule autour de 5 types d'objets clés : Territoire, Acteur, Produit, Flux, Stock. La structuration de la donnée
consiste ainsi à créer dans la base les différents types d'objets et d'y associer des propriétés. 

Par exemple : Un territoire ou un acteur sera associé à son nom, à son code, à sa hiérarchie territoriale, 
et à toute autre donnée (sa population, sa superficie, ...). Un flux sera une 
quantité (en kg, en euros, en unité, ...) d'un produit associé à un territoire ou un acteur. 

***Précision importante*** : il existe 2 types de flux : ceux dont on connaît l'origine et la destination 
(appelés `Pathflow`) et ceux dont on ne connaît que l'endroit où il se manifeste (appelés `Gateflow`). *
Par exemple la donnée de consommation éléctrique d'un territoire est un Gateflow car on ne connaît pas l'origine 
de la production. Mais le déplacement d'un individu d'un endroit A vers un endroit B est un Pathflow.

En résumé, Sinamet offre la possibilité de manipuler 6 classes d'objets : 
`Territoiry`, `Actor`, `Product`, `Gateflow`, `Pathflow`, `Stock`. 
Ces objets héritent tous d'une classe mère `MTObject`, et les flux et stocks héritent également de `MTQuantifiable`.
Vous trouverez [à cette page](../documentation/mtobjecttypes.md) 
une description plus détaillée des différents types d'objets.

Dans la suite du tutoriel, nous expliquons comment importer les données, puis comment les requêter.


## Base de données et Programmation Orientée Objet

Un des intérêts de Sinamet est d'offrir un paradigme de programmation orientée objet pour l'analyse des flux 
territorialisés, plutôt que de devoir recourir à des requêtes SQL, qui peuvent être rapidement complexes
à élaborer. Cela apporte une plus grande intuitivité dans l'élaboration des traitements.

Les différents types d'objets sont présentés précédemment. Les liens entre la base de données PostgreSQL/Postgis 
et les objets Python sont assurés gâce à un Mapping objet-relationnel
(qui repose sur la librairie <a href="https://www.sqlalchemy.org/" target="_blank">SQLAlchemy</a> et son extension spatiale
<a href="https://geoalchemy-2.readthedocs.io/en/stable/" target="_blank">GeoAlchemy 2</a>).

In fine, l'utilisateur peut donc manipuler des objets de données (des territoires, des acteurs, des flux, ...) 
sans avoir à s'occuper de la structuration de l'information en base. Cela dit, il reste possible pour l'utilisateur
de construire directement des requêtes SQL.


## Suite du tutoriel

Dans la suite du tutoriel, nous verrons d'autres usages plus avancés permis par Sinamet :

* [Premier modèle](../quickstart/firstmodel.md)
* [Importation en masse de données](../quickstart/moduleimport.md)
* [Requêter les données](../quickstart/requesting.md)


