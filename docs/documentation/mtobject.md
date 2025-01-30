# Méthodes des MTObject

Tous les objets du modèle (sauf les propriétés) héritent de la classe MTObject, 
et les objets quantifiables héritent de MTQuantifiables. 
Les fonctions ci-dessous sont donc accessibles pour tous les objets.


::: mtobjects.mtobject.MTObject
    options:
        show_root_heading: true
        show_bases: false
        members:
        - get_code
        - get_name
        - get_property
        - get_property_gen
        - get_codes
        - get_names
        - get_properties
        - get_properties_gen
        - get_source_ref
        - get_children
        - is_in

::: mtobjects.quantifiable.MTQuantifiable
    options:
        show_root_heading: true
        show_bases: false
        members:
        - get_quantity
