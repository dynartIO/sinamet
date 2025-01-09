from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from sqlalchemy import select

from sinamet.mtobjects.actor import Actor
from sinamet.mtobjects.territory import Territory
from sinamet.mtobjects.product import Product
from sinamet.mtobjects.property import Property

if TYPE_CHECKING:
    from sqlalchemy import Select


class SidbStatic:
    @staticmethod
    def get_mtobject_children(mtobject: Territory | Actor | Product,
                              cache_properties: list[str] = [],
                              return_type: Literal['qid', 'queryid',
                                                   'query', 'id',
                                                   'list', 'object',
                                                   'count'] = 'list'
                              ) -> (list[Territory] | list[Actor] |
                                    list[Product] | list[int] |
                                    Select | int):
        """Récupère les enfants directs d'un objet.

        Parameters:
            mtobject: L'objet dont on souhaite récupérer les enfants.
            cache_properties: Liste de propriétés à mettre en cache.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.

        Returns:
            (list[Territory] | list[Actor] | list[Product]): La liste des objets.
            (list[int]): La liste des identifiants des objets.
            (int): Le nombre d'objets.
            (Select): La requête des objets ou des identifiants.

        Note: FutureDev
            Implémenter profondeur.
        """
        from sinamet.sidb import Sidb

        sidb = Sidb.get_sidb_from_object(mtobject)

        if not isinstance(mtobject, (Territory, Actor, Product)):
            raise TypeError(f'Incorrect object type, got {type(mtobject)}')

        object_class = type(mtobject)

        q = {}
        for nq, targetq in zip(["id", "object"], [object_class.id, object_class]):
            q[nq] = select(targetq).join(object_class.properties)
            q[nq] = q[nq].where(Property.name_a == f"IsIn{object_class.__name__}")
            q[nq] = q[nq].where(Property.value_mtobject_id == mtobject.id)

        result = sidb.compute_query_return_type(q, return_type)
        sidb.compute_query_cache_properties(cache_properties, return_type, q['id'])

        return result

    @staticmethod
    def get_mtobject_parents(mtobject: Territory | Actor | Product,
                             cache_properties: list[str] = [],
                             return_type: Literal['qid', 'queryid',
                                                  'query', 'id',
                                                  'list', 'object',
                                                  'count'] = 'list'
                             ) -> (list[Territory] | list[Actor] |
                                   list[Product] | list[int] |
                                   Select | int):
        """Récupère les parents directs d'un objet.

        Parameters:
            mtobject: L'objet dont on souhaite récupérer les parents.
            cache_properties: Liste de propriétés à mettre en cache.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.

        Returns:
            (list[Territory] | list[Actor] | list[Product]): La liste des objets.
            (list[int]): La liste des identifiants des objets.
            (int): Le nombre d'objets.
            (Select): La requête des objets ou des identifiants.

        Note: FutureDev
            Implémenter profondeur.
        """
        from sinamet.sidb import Sidb

        sidb = Sidb.get_sidb_from_object(mtobject)

        if not isinstance(mtobject, (Territory, Actor, Product)):
            raise TypeError(f'Incorrect object type, got {type(mtobject)}')

        object_class = type(mtobject)

        q = {}
        for nq, targetq in zip(["id", "object"], [object_class.id, object_class]):
            q[nq] = select(targetq).join(object_class.properties)
            q[nq] = q[nq].where(Property.name_a == f"IsIn{object_class.__name__}")
            q[nq] = q[nq].where(Property.item_id == mtobject.id)

        result = sidb.compute_query_return_type(q, return_type)
        sidb.compute_query_cache_properties(cache_properties, return_type, q['id'])

        return result

    @staticmethod
    def get_one_mtobject_read_kw_arg(*args, **kwargs):
        """ Analyse les args et kwargs pour identifier le nom de l'attribut
        et sa valeur \n
        :return: (Nom de l'attribut, Valeur de l'attribut)
        :rtype: (string, string)
        :todo: Permettre une recherche avec noms ou codes multiples\
        (actuellement un seul code ou (exclusif) nom possible)
        """

        if len(args) == 0:  # Cas où les infos viennent des kwargs
            items = ["code", "name", "id"]
            # Si un "code" est indiqué, il prend le pas sur le nom
            attribute_name = []
            attribute_value = []

            for item in items:
                keyval_temp = [(key, val) for key, val in kwargs.items()
                               if (key.startswith(item+"_") or key == item)
                               and val is not None and val != ""]
                if len(keyval_temp) > 1:
                    raise AttributeError(f"Several kwargs for '{item}' has been indicated")
                elif len(keyval_temp) == 1:  # Un seul code utilisé
                    temp_key = keyval_temp[0][0]
                    temp_key = str.capitalize(temp_key.replace(item+"_", item+"@"))
                    attribute_name = temp_key
                    attribute_value = keyval_temp[0][1]
                    break

        elif len(args) == 1:  # Cas d'un objet de requete
            try:
                valuearg = args[0].split("(")[1]
                valuearg = valuearg.replace(")", "")
                tabarg = valuearg.split("=")
                attribute_name = tabarg[0]
                attribute_value = tabarg[1]
            except IndexError:
                return f"Parameter string '{args[0]}' not recognized"

        elif len(args) == 2:  # Cas où les infos viennent des args
            attribute_name = args[0]
            attribute_value = args[1]
        else:
            # Should not reach that point : Error of value otherwise
            raise AttributeError(f"Not identified = {str(args)} / {str(kwargs)}")

        # Un attribut => Retourne doublet, plusieurs attributs => Retourne doublet listes
        try:
            if len(attribute_name) == 1:
                return (attribute_name[0], attribute_value[0])
            elif len(attribute_name) == 0:
                raise AttributeError(f"Not identified = {str(args)} / {str(kwargs)}")
            else:
                # Ne devrait pas arriver (cf todo)
                return (attribute_name, attribute_value)
        except TypeError as msg:
            print(f"(attribute_name, attribute_value)=({attribute_name}, {attribute_value})")
            raise TypeError(str(msg))

    @staticmethod
    def subquery_recursive(object_type, list_fields, id_start, key):
        if isinstance(id_start, int):
            subquery = select(*list_fields).where(object_type.id == id_start).cte(recursive=True)
        elif isinstance(id_start, (list, set, tuple)):
            subquery = select(*list_fields).where(object_type.id.in_(id_start)).cte(recursive=True)

        # partie centrale
        subquery = subquery.union(
                # on passe par l'attribut IsInTerritory de value_mtobject_id correspondant à l'un de ceux
                # de la requête précédente, Attribute.item_id permet de descendre d'un niveau
                select(*list_fields)
                .where(Property.name_a == key)
                .where(Property.item_id == object_type.id)
                .where(Property.value_mtobject_id == subquery.c.id)
        )
        return subquery

    @staticmethod
    def subquery_recursive_reverse(object_type, list_fields, id_start, key):
        if isinstance(id_start, int):
            id_start = {id_start}

        subquery = select(*list_fields).where(object_type.id.in_(id_start)).cte(recursive=True)

        # partie centrale
        subquery = subquery.union(
                # on passe par l'attribut IsInTerritory de value_mtobject_id correspondant à l'un de ceux
                # de la requête précédente, Attribute.item_id permet de descendre d'un niveau
                select(*list_fields)
                .where(Property.name_a == key)
                .where(Property.item_id == subquery.c.id)
                .where(Property.value_mtobject_id == object_type.id)
        )
        return subquery

    @staticmethod
    def get_mtobjecttype_from_classname(classname: str):
        if type(classname) is not str:
            raise AttributeError("Unknown classname type '%s', str expected" % classname)
        if classname.lower() == 'actor':
            return Actor
        elif classname.lower() == 'territory':
            return Territory
        elif classname.lower() == 'product':
            return Product
        else:
            raise AttributeError("'%s' type not supported yet #Todo")
