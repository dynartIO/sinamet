# Outils

Sinamet est accompagnés de quelques outils supplémentaires qui viennent faciliter le fonctionnement de la librarie.
Ils ne sont pas strictement nécessaire à la manipulation des données à travers l'ORM, mais servent à standardiser
et simplifier certaines opérations en lien avec l'analyse des flux.

## Profile 

`Profile` transforme une liste de flux ou de stock en un profil temporel, 
c'est à dire une liste de tuplets (valeur, date). Ces profils temporels peuvent être ainsi facilement affichés 
sur un graphique. Voici l'idée en quelques lignes :

```python
from sinamet.tools import Profile
with Sidb.connect() as sidb:
    lst_flux = sidb.get_import( ) #A Completer avec la cible
    profile = Profile.build(lst_flux, unit='kWh')
    plot(x=profile.times, y=profile.value)
```

Les opérations mathématiques simples (addition, soustraction, multiplication, division) sont directement applicables
sur les profils.

::: tools.profile.Profile
    options:
        members: no
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3


::: tools.profile.Profile.get_value
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 4


## Conversion d'unités

Un utilitaire de conversion d'unités est disponible dans Sinamet. 
Il dispose de coefficients standards (L en m3, J en Wh ou tep ou cal, m2 en ha, t en kg), 
gère les préfixes d'unités (k, M, G, T, ...)
et peut utiliser des coefficients complémentaires pour réaliser les conversions.

::: tools.unitconverter.convert
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3


## Dictsyntax

Dictsyntax peut être utilisé pour structurer de manière standard les données traitées d'un module.
Il permet de distinguer les paramètres (s, 'sets'), les données brutes (r, 'results'), et les données complémentaires 
graphiques (g, 'graphicsinfo') dans un dictionnaire (généralement appelé data). Par exemple :

    from sinamet.tools.dictsyntax import r, s, g    
    data = {s: [], r:[], g:[]}

## Xstring

Permet de réaliser des opérations autour des chaînes de caractère (simplification, hachage).

::: tools.xstring.hexhash
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: tools.xstring.alphanumhash
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

::: tools.xstring.minimize
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3

*[A détailler]*

## Xtime

Permet de réaliser des opérations autour des dates.

*[A détailler]*

## Path

Permet d'accéder à des chemins de dossier standard pour chaque package (dossier "data", "build", "cache")

*[A détailler]*


