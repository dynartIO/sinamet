### Installer les dépendances Python

Si vous souhaitez installer Sinamet depuis le code source, ajouté au Python
Sinamet nécessite l'installation préalable des librairies suivantes:

    anytree>=2.12.1
    GeoAlchemy2>=0.16.0
    numpy>=2.2.1
    pandas>=2.2.3
    psycopg2-binary>=2.9.10
    shapely>=2.0.6
    SQLAlchemy>=2.0.36
    Unidecode>=1.3.8

# Outils de développement

Ce fichier contient des éléments destinés aux développeurs.
Il ne fait pas partie de la documentation officielle. 
Il convient donc d'utiliser ces éléments avec précaution : il ne comprennent aucun garantie (de lisibilité,
de bon fonctionnement, d'exhaustitivité) !

## Créer une base de données:

Les lignes suivantes sont des aides à la création d'une base de données. Il ne remplacent pas la documentation
officielle.

### En ligne de commande

    psql -c ALTER USER postgres with encrypted password 'your_password';

Eventuellement :

    sudo -u postgres psql -c ALTER USER postgres with encrypted password 'your_password';
    sudo systemctl restart postgresql.service

### Via pgAdmin 4

Dans pgAdmin : se connecter à l’instance

* Register server 
    * General / Name = SinametLocal *(ou n’importe quoi)*
    * Host name : localhost
    * Password : postgres *(selon configuration initiale)*
* Login/GroupRoles / Bouton droit / Create ... > Login Groupe Role
    * Créer un utilisateur : id = projetsinamet1_user / mdp = projetsinamet1_pass
    * Password = projetsinamet1_pass
    * Privilieges : Can_Login
* Create database
    * Database : projetsinamet1_db
    * Owner : projetsinamet1_user

## Ressources complémentaire

Pour la création d'une base de données Postgres/PostGis

* [https://ubuntu.com/server/docs/install-and-configure-postgresql](https://ubuntu.com/server/docs/install-and-configure-postgresql)
* [https://data.sigea.educagri.fr/download/sigea/supports/PostGIS/distance/initiation/PostGIS_Installation/co/Installer_Ubuntu.html](https://data.sigea.educagri.fr/download/sigea/supports/PostGIS/distance/initiation/PostGIS_Installation/co/Installer_Ubuntu.html)
* Tutoriel installer PgAdmin4 (Ubuntu) : 
[https://www.webhi.com/how-to/fr/comment-installer-pgadmin4-sur-ubuntu-18-04-20-04-22-04/](https://www.webhi.com/how-to/fr/comment-installer-pgadmin4-sur-ubuntu-18-04-20-04-22-04/)

## Installer GDAL

Sinamet s'appuie sur la librarie GDAL pour la manipulation de l'information géographique. Cette 
librairie peut être compliquée à installer, en particulier sur Windows. Voici quelques astuces qui
peuvent vous aider dans cette installation.

#### Sur Windows

Nous suggérons d'installer d'abord la roue (Wheel) disponible pour gdal à cette adresse:
[https://github.com/cgohlke/geospatial-wheels/releases](https://github.com/cgohlke/geospatial-wheels/releases)

    $ pip install nom_du_fichier_wheel_gdal.whl

#### Sur Linux

Il est nécessaire d'installer les packages suivants avant l'installation de GDAL via pip:

    # apt-get install -y libgdal-dev gdal-bin proj-bin libproj-dev g++

