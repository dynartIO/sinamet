# Foire aux questions

Si vous ne trouvez pas de réponse à votre question, n'hésitez pas à nous contacter contact@sinamet.tech

## Quelles sont les fonctionnalités de Sinamet ?

Sinamet est une boîte à outil dédiée à l'analyse des flux à des échelles territoriales.
Elle inclut les fonctionnalités suivantes :

- L'organisation d'une base de données centralisée,
- La gestion de nomenclatures de produits, et de la conversion entre nomenclatures,
- La gestion et la conversion d'unités de quantification,
- La hiérarchisation et la description de territoires et d'acteurs,
- La gestion de données datées, et leur aggrégation,
- La traçabilité des données,
- La gestion de plusieurs clés primaires (notamment pour les territoires et acteurs),
- La gestion d'alias et de noms multiples (par exemple en plusieurs langues),
- La gestion des projections géographiques,
- Un paradigme algorithmique orienté objet.


## Comment réinitialiser la base de données ?

Pour réinitialiser la base de données, il suffit d'éxecuter les lignes suivantes :

    with Sidb.connect() as sidb:
        sidb.reset()


## Au premier lancement de Sinamet, j'obtiens une erreur de géométrie ...

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedObject) type "geometry" does not exist
LINE 10:  value_geo geometry(GEOMETRY,-1),
```

Cette erreur survient si Postgis n'est pas installé sur la base de données liée à Sinamet.
Pour l'installer, il faut exécuter le script SQL suivant :

    CREATE EXTENSION postgis;
    CREATE EXTENSION unaccent;