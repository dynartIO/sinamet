# Installation

Sinamet nécessite `Python >= 3.11`.

## Installer la librarie

Sinamet peut être simplement installée avec Pip :

    pip install sinamet

### Dépendances complémentaires

Nous conseillons également d'installer ces librairies, qui ne sont pas strictement nécessaires pour faire
fonctionner Sinamet, mais qui sont nécessaires pour l'exécution des fichiers de démo.

    geopandas>=1.0.1
    xlrd>=2.0.1
    openpyxl>=3.1.5

## Installer une base de données PostreSQL/PostGIS

Sinamet nécessite de pouvoir accéder à une base de données PostgreSQL dédiée, avec les extensions 
Postgis et Unaccent activées.

Nous recommandons de se référer à la documentation officielle pour l'installation de PostgreSQL/PostGIS.
Eventuellement, vous pouvez également vous aider de
[ce tutoriel (non officiel)](https://data.sigea.educagri.fr/download/sigea/supports/PostGIS/distance/initiation/PostGIS_Installation/co/PostGIS_Installation_3.html).

Une fois PostgreSQL/PostGIS installés, il s'agit de créer une base de données. À titre d'exemple, nous créons une
base de données avec les identifiants d’accès à la base de données suivants :

    NAME = projetsinamet1_db
    USER = projetsinamet1_user
    PASS = projetsinamet1_pass
    HOST = localhost
    PORT = 5432

Les extensions `postgis` et `unaccent` doivent être activées. Pour cela, il suffit d'exécuter les commandes SQL 
suivantes depuis la base de données nouvellement créée.

    CREATE EXTENSION postgis;
    CREATE EXTENSION unaccent;

## Créer un fichier de configuration

Afin de ne pas avoir à faire figurer les identifiants de la base de données dans chaque script,
la librairie Sinamet peut être étendue avec un fichier de configuration TOML.

Vous devez ainsi créer un fichier `sinamet_config.toml` dans le dossier d'éxecution des scripts ou un
de ses parents.

Ce fichier reprend la configuration de la base de donnée, voici un simple exemple :
```toml
COREDB_USER = 'projetsinamet1_user'
COREDB_PASS = 'projetsinamet1_pass'
COREDB_NAME = 'projetsinamet1_db'
COREDB_HOST = 'localhost'
COREDB_PORT = '5432'
```
Il est également possible de renseigner directement le chemin complet de la base
de donnée sous la forme :
```
postgresql://{username}:{password}@{host}:{port}/{db}
```
Ce qui nous donne :
```toml
COREDB_PATH = 'postgresql://projetsinamet1_user:projetsinamet1_pass@localhost:5432/projetsinamet1_db'
```

### Configuration avancée pour une utilisation multi-environements

Pour utiliser plusieurs bases de données/environements et ne pas avoir à réécrire
un fichier toml pour chacune, vous pouvez séparer leurs identifiants respectifs
dans des sections, puis indiquer l'environement à utiliser avec une variable
`current_env`. Exemple :
```toml
current_env = 'projetsinamet1'

[projetsinamet1]
COREDB_PATH = 'postgresql://projetsinamet1_user:projetsinamet1_pass@localhost:5432/projetsinamet1_db'

[projetsinamet2]
COREDB_PATH = 'postgresql://projetsinamet2_user:projetsinamet2_pass@localhost:5432/projetsinamet2_db'
```

Ainsi, il suffit de changer cette variable `current_env` pour passer d'un environnement à l'autre.
