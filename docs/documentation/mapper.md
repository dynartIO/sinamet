# Mapper

::: core.mapper.Mapper

## Notes sur les clés primaires et étrangères

### Clé primaire
Une propriété identifiée comme clé primaire (valable uniquement pour Code ou Name) dans un mapper signifie qu'au chargement
du mapper, Sinamet va vérifier si la propiété existe déjà dans la base de donnée. Si la propriété existe, l'objet
associé est récupéré et mis à jour avec le mapper. Si non un nouvel objet est créé. Il est possible d’indiquer 
plusieurs clés primaires, il suffit que l’une d’elle pointe vers un objet pour qu’il soit mis à jour. 
Attention, Sinamet ne vérifie pas les clé primaires multiples et contradictoires (un seul mapper avec des clés 
primaires qui pointent vers différents objets). Seul le premier objet trouvé est dans ce cas mis à jour.

### Clé étrangère
Clé étrangère : Sinamet vérifie si un objet est déjà référencé dans la base avec cette clé (uniquement Code ou Name). 
Si oui, le chargement du Mapper doit mettre à jour cet objet, si non, une erreur est levée.

### Comportement par défaut
Si aucune clé primaire ou étrangère n'est renseignée, toutes les propriétés "Code" ou "Name" sont considérées comme
clé primaire. Ainsi, il est souvent préférable de désigner explicitement la clé primaire dans un mapper, pour éviter
les ambiguités.
