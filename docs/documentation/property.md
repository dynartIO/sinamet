# Propriétés (Property)

Tous les MTObjects sont associées à des propriétés. Ces propriétés peuvent être de différents types : 
litéral (texte, nombre), relation (avec un autre MTObject), ou forme géographique (point, ligne, polygone).
Les propriétés peuvent être datées et tracées.

Les objets propriétés sont constitués de :

* Un `item`, c'est-à-dire le `MTObject` auquel se réfère la propriété
* Un nom (qui peut être en 2 parties, séparé par `@`)
* Une valeur (litéral, MTObject ou forme géographique),
* Une source (`source_ref`), optionnelle mais fortement conseillée,
* Une temporalité à travers une date (`date_point`) ou une période (`date_start` > `date_end`)


::: mtobjects.property.Property
    options:
        members: no
        show_root_heading: true
        show_root_full_path: false
        heading_level: 2


::: mtobjects.property.Property.get_name
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3


::: mtobjects.property.Property.get_value
    options:
        show_root_heading: true
        show_root_full_path: false
        heading_level: 3