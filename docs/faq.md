# Foire aux questions

En cours de réalisation ...

## Comment réinitialiser la base de données

Pour réinitiliser la base de données, il suffit d'éxecuter les lignes suivantes :

    with Sidb.connect() as sidb:
        sidb.reset()


## Au premier lancement de Sinamet, j'obtiens une erreur de géométrie

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedObject) type "geometry" does not exist
LINE 10:  value_geo geometry(GEOMETRY,-1),
```

Cette erreur survient si Postgis n'est pas installé sur la base de données liée à Sinamet.
Pour l'installer, il faut exécuter le script SQL suivant :

    CREATE EXTENSION postgis;
    CREATE EXTENSION unaccent;