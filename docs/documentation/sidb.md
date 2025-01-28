# Sidb

Sidb est l'accronyme de Sinamet Database. Il sert d'interface pour les requêtes sur la base de données, 
notamment pour y récupérer les différents objets à manipuler (Territoires, Acteurs, Flux...).

L'utilisation de l'interface Sidb doit se faire à travers un contexte `with` pour la connexion (voir code ci-dessous).
Les objets ne sont pas persistants d'un contexte à l'autre.

```python
with Sidb.connect() as sidb:
    mon_territoire = sidb.get_territory( ... )
```

## Récupérer un objet

::: sidb.territory.SidbTerritory.get_territory
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.actor.SidbActor.get_actor
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.product.SidbProduct.get_product
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

## Récupérer une liste d'objets

::: sidb.territory.SidbTerritory.get_territories
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.actor.SidbActor.get_actors
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.product.SidbProduct.get_products
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.product.SidbProduct.get_product_list
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.gateflow.SidbGateflow.get_gateflows
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.gateflow.SidbGateflow.get_inputs
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.gateflow.SidbGateflow.get_outputs
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.gateflow.SidbGateflow.get_consumptions
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.gateflow.SidbGateflow.get_productions
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.gateflow.SidbGateflow.get_extractions
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.gateflow.SidbGateflow.get_emissions
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.pathflow.SidbPathflow.get_pathflows
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.pathflow.SidbPathflow.get_imports
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.pathflow.SidbPathflow.get_exports
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.pathflow.SidbPathflow.get_internals
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.stock.SidbStock.get_stocks
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

## Récupérer une liste d'objets contenus dans un autre

::: sidb.territory.SidbTerritory.get_territories_in
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.actor.SidbActor.get_actors_in
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.product.SidbProduct.get_products_in
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

## Récupérer une liste d'objets en contenant un autre

::: sidb.territory.SidbTerritory.get_territories_on
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.actor.SidbActor.get_actors_on
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.product.SidbProduct.get_products_on
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

## Autres fonctions

::: sidb.Sidb.get_sourcerefs
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.get_statistics
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.get_properties
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.get_property_with_id
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.get_distinct_property_values
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.is_loaded
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.is_not_loaded
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

## Supprimer des données

::: sidb.Sidb.delete
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.delete_sourceref
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.reset
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3


## Charger des données

::: sidb.Sidb.load
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: sidb.Sidb.progress
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

## Générateur de contexte

::: sidb.Sidb.connect
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3