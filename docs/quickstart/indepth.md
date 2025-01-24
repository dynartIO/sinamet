# Appronfondissement

Cette page vise à présenter des fonctionnalités complémentaires intégrées à Sinamet.

## Suivi des sources de données

Il est conseillé d'associer les données à une source de données pour pouvoir les retracer. Cela se fait à la création
des Mapper.

```python
mapper = Mapper("Territory", source_ref='nom_source_ref')
```

Cela peut aussi se faire pour une propriété en particulier :

```python
mapper.add("Propriete", source_ref='nom_source_ref')
```

## Clés primaires et étrangères

Par défaut, lors du chargement d'un [`Mapper`](../documentation/mapper.md), Sinamet considère les propriétés 
`Code` ou `Name` comme des clés primaires. C'est-à-dire que si un objet avec ce nom ou ce code est présent dans
la base de données, il sera mis à jour lors du chargement du [`Mapper`](../documentation/mapper.md). 
Les nouvelles propriétés seront ajoutées,
mais aucune nouvelle instance de territoire, d'acteur ou de produit ne sera créé.

Pour éviter les ambiguités, il est recommandé d'indiquer explicitement les clés primaires du 
[`Mapper`](../documentation/mapper.md) lors
de l'ajout d'une propriété `Code` ou `Name`. 

```python
mapper.add("Code", "ValeurPropriete", primary_key=True)
```

Il peut aussi être fait usage d'une clé étrangère.

### Clé primaire
Une propriété identifiée comme clé primaire (valable uniquement pour Code ou Name) dans un
[`Mapper`](../documentation/mapper.md) signifie qu'au chargement
du [`Mapper`](../documentation/mapper.md), Sinamet va vérifier si la propiété existe déjà dans la base de donnée. 
Si la propriété existe, l'objet
associé est récupéré et mis à jour avec le mapper. Si non un nouvel objet est créé. Il est possible d’indiquer 
plusieurs clés primaires, il suffit que l’une d’elle pointe vers un objet pour qu’il soit mis à jour. 
Attention, Sinamet ne vérifie pas les clés primaires multiples et contradictoires 
(un seul [`Mapper`](../documentation/mapper.md) avec des clés 
primaires qui pointent vers différents objets). Seul le premier objet trouvé est dans ce cas mis à jour.

### Clé étrangère
Clé étrangère : Sinamet vérifie si un objet est déjà référencé dans la base avec cette clé (uniquement Code ou Name). 
Si oui, le chargement du [`Mapper`](../documentation/mapper.md)
doit mettre à jour cet objet, si non, une erreur SidbNotFoundError est levée.


## Gestion des unités

[ A venir ]

## Construire et manipuler des profils (Profile)

[ A venir ]

## Travailler avec les origines / destinations

[ A venir ]