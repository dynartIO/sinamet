# Outils

Sinamet est accompagnés de quelques outils supplémentaires qui viennent faciliter le fonctionnement de la librarie.
Ils ne sont pas strictement nécessaire à la manipulation des données à travers l'ORM, mais servent à standardiser
et simplifier certaines opérations en lien avec l'analyse des flux.

***Plus de détails à venir***

## Profile 

`Profile` transforme une liste de flux ou de stock en un profil temporel, 
c'est à dire une liste de tuplets (valeur, date). Ces profils temporels peuvent être ainsi facilement affichés 
sur un graphique. Voici l'idée en quelques lignes (*à affiner*)

        from sinamet.tools import Profile
        lst_flux = get_import(____)
        profile = Profile.build(lst_flux, unit='kWh')
        plot(x=profile.times, y=profile.value)

Les opérations mathématiques simples (addition, soustraction, multiplication, division) sont directement applicables
sur les profils.

## UnitConverter

Utilitaire de conversion d'unités. 
Dispose de coefficients standards (L en m3, J en Wh ou tep ou cal, m2 en ha, t en kg)

    from sinamet.tools.unitconvert import convert
    convert(12, 't', 'kg') # Converti des tonnes en kilo.

Gère les préfixes d'unités

    convert(12, 'k€', '€') # Converti des kilo-euros en euros.

Possibilité d'ajouter des coefficients de conversion

    convert(1378, 'kg', 'm3', coeffdic={"g/cm3":7.874}) # converti des kg de fer en m3 (densité fer : 7,874 g/cm3)

## Dictsyntax

Dictsyntax peut être utilisé pour structurer de manière standard les données traitées d'un module.
Il permet de distinguer les paramètres (s, 'sets'), les données brutes (r, 'results'), et les données complémentaires 
graphiques (g, 'graphicsinfo') dans un dictionnaire (généralement appelé data)

    from sinamet.tools.dictsyntax import r, s, g    
    data = {s: [], r:[], g[]}

## Opestring

Permet de réaliser des opérations autour des chaine de caractère. Dispose en particulier d'une fonction
de hachage.

## timext

Permet de réaliser des opérations autour des dates.

## Path

Permet d'accéder à des chemins de dossier standard pour chaque package (dossier "data", "build", "cache")


