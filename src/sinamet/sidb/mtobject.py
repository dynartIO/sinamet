import warnings

from datetime import date

from typing import Literal, Iterable

from sqlalchemy.sql import func, select, or_, and_, Select
from sqlalchemy.orm import aliased

from sinamet.sidb.static import SidbStatic
from sinamet.mtobjects.mtobject import MTObject
from sinamet.mtobjects.actor import Actor
from sinamet.mtobjects.territory import Territory
from sinamet.mtobjects.product import Product
from sinamet.mtobjects.property import Property
from sinamet.mtobjects.pathflow import Pathflow
from sinamet.mtobjects.gateflow import Gateflow
from sinamet.mtobjects.stock import Stock
from sinamet.errors import SidbNotFoundError, SidbMultiFoundError
from sinamet.tools.timext import to_date, get_start_end_dates


class SidbMTObject:
    def get_mtobject_with_id(self, id: int) -> MTObject:
        """Renvoie l'objet correspondant à un identifiant."""
        return self.session.get(MTObject, id)

    def get_mtobject_tap(self,
                         mtobject_class: type[Territory | Actor | Product],
                         *args,
                         like_value: bool = False,
                         case_value: bool = True,
                         accent_value: bool = True,
                         return_type: Literal['object', 'id',
                                              'queryid', 'qid',
                                              'query'] = 'object',
                         raise_none: bool = True,
                         multi: Literal['raise', 'warn_first',
                                        'warn_list', 'first',
                                        'list'] = "warn_list",
                         nomenclature: str | None = None,
                         verbose: bool = False,
                         deep_verbose: bool = False,
                         **kwargs
                         ) -> Territory | Actor | Product | int | Select | None:

        if mtobject_class not in [Actor, Territory, Product]:
            raise TypeError(f"mtobject_class has to be Actor, Territory or Product, got {mtobject_class}")
        if return_type not in (_list := ["object", "id", "queryid", "qid", "query"]):
            raise ValueError(f"return_type can only be one of {_list}, got {return_type}")
        if multi not in (_list := ["raise", "warn_first", "warn_list", "first", "list"]):
            raise ValueError(f"many can only be one of {_list}, got {multi}")

        key, value = SidbStatic.get_one_mtobject_read_kw_arg(*args, **kwargs)
        if verbose:
            print(f'key = {key}, value = {value}')

        # Recherche dans le cache si recherche sur clé exacte uniquement
        if key != "Id" and not like_value and case_value and accent_value:
            if verbose:
                print("Looking for object in cache ...")
            cached_object = self.get_one_mtobject_from_cache(mtobject_class.__name__,
                                                             key, value, nomenclature)
            if cached_object:
                if verbose:
                    print("Found in cache and returned : ", cached_object)
                return cached_object

        # Si pas dans le cache -> requete
        if verbose:
            print("Creating query ...")
        q = {}
        for nq, targetq in zip(["id", "object"], [mtobject_class.id, mtobject_class]):
            q[nq] = select(targetq)
            q[nq] = q[nq].join(mtobject_class.properties)
            if key == "Id":
                q[nq] = q[nq].where(mtobject_class.id == value)
            else:
                # Gestion de la casse (case_value) et/ou de l'accentuation (accent_value)
                prop = Property.value_literal if accent_value else func.unaccent(Property.value_literal)
                prop = prop if case_value else func.lower(prop)
                value = value if accent_value else func.unaccent(value)
                value = value if case_value else func.lower(value)

                if like_value:
                    q[nq] = q[nq].where(prop.like(value))
                else:
                    q[nq] = q[nq].where(prop == value)

                prop_a, *prop_b = key.split('@', 1)
                if verbose:
                    print(f'prop_a = {prop_a}, prop_b = {prop_b}')
                q[nq] = q[nq].where((Property.name_a == prop_a) |
                                    (Property.name_a == prop_a + "Alias"))
                if prop_b:
                    q[nq] = q[nq].where(Property.name_b == prop_b[0])

                if (mtobject_class is Product) and nomenclature:
                    prop_nomenclature = aliased(Property)
                    q[nq] = q[nq].join(prop_nomenclature, mtobject_class.properties)
                    q[nq] = q[nq].where((prop_nomenclature.name_a == 'Nomenclature')
                                        & (prop_nomenclature.value_literal == nomenclature))

        if verbose:
            print("Build query = ", q["object"])

        result = self.compute_query_return_type(q, return_type)
        if isinstance(result, Select):
            return result
        if verbose:
            print(result, len(result))

        # Gestion des résultats selon leur nombre : 0, 1 ou +
        if not len(result):
            if raise_none:
                raise SidbNotFoundError(f"No such object has been found in the database ({key}={value})")
            return None
        if len(result) == 1:
            if key != "Id" and not like_value and case_value and accent_value:
                self.set_cache_mtobject_codename(result[0], key, value, False, prefix=nomenclature)
            self.cache_mtobject_properties(result[0])
            return result[0]
        match multi:
            case "raise":
                raise SidbMultiFoundError("Several corresponding objects.")
            case "warn_list":
                warnings.warn(f"Several corresponding objects ({key}={value}), returning all")
                self.get_properties(["Name", "Code"], map_id=q["id"])
                return result
            case "warn_first":
                warnings.warn(f"Several corresponding objects ({key}={value}), returning first")
                self.cache_mtobject_properties(result[0])
                return result[0]
            case "first":
                self.cache_mtobject_properties(result[0])
                return result[0]
            case "list":
                self.get_properties(["Name", "Code"], map_id=q["id"])
                return result

    def get_mtobjects_tap(self,
                          mtobject_class: type[Territory | Actor | Product],
                          *args,
                          like_value: bool = False,
                          case_value: bool = True,
                          accent_value: bool = True,
                          map_id: Iterable[int] | int | Select = [],
                          return_type: Literal['list', 'object',
                                               'id', 'queryid', 'qid',
                                               'query', 'count'] = 'list',
                          cache_properties: list[str] = [],
                          nomenclature: str | None = None,
                          verbose: bool = False,
                          deep_verbose: bool = False
                          ) -> (list[Territory] | list[Actor] | list[Product] |
                                list[int] | Select | int):
        if mtobject_class not in [Actor, Territory, Product]:
            raise TypeError(f"mtobject_class has to be Actor, Territory or Product, got '{mtobject_class}'.")
        if return_type not in (_list := ["list", "object", "id", "queryid", "qid", "query", "count"]):
            raise ValueError(f"return_type can only be one of {_list}, got '{return_type}'.")

        q = {}
        for nq, targetq in zip(["id", "object"], [mtobject_class.id, mtobject_class]):
            q[nq] = select(targetq)

            # Add an id filter.
            if map_id:
                if isinstance(map_id, int):
                    map_id = (map_id,)
                q[nq] = q[nq].where(mtobject_class.id.in_(map_id))

            # Add a nomenclature filter.
            if mtobject_class is Product and nomenclature:
                prop_nomenclature = aliased(Property)
                q[nq] = q[nq].join(prop_nomenclature, mtobject_class.properties)
                q[nq] = q[nq].where((prop_nomenclature.name_a == 'Nomenclature')
                                    & (prop_nomenclature.value_literal == nomenclature))

            # If no arguments were given, no need to filter properties.
            if not len(args):
                continue
            q[nq] = q[nq].join(mtobject_class.properties)

            key, value = args[0], args[1]

            # Add a filter for the properties' values.
            if value != "*":
                prop = Property.value_literal if accent_value else func.unaccent(Property.value_literal)
                prop = prop if case_value else func.lower(prop)
                value = value if accent_value else func.unaccent(value)
                value = value if case_value else func.lower(value)
                if like_value:
                    q[nq] = q[nq].where(prop.like(value))
                else:
                    q[nq] = q[nq].where(prop == value)

            propname_a, *propname_b = key.split('@', 1)
            q[nq] = q[nq].where(Property.name_a == propname_a)
            if propname_b:
                q[nq] = q[nq].where(Property.name_b == propname_b[0])

        result = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return result

    def get_mtobjects_by_ids(self,
                             type_mtobject: type[Territory | Actor | Product |
                                                 Gateflow | Pathflow | Stock],
                             ids: list[int] | int,
                             cache_properties: list[str] = [],
                             return_type: Literal['list',
                                                  'object',
                                                  'query',
                                                  'queryid',
                                                  'qid',
                                                  'count',
                                                  ] = "list",
                             verbose: bool = False
                             ) -> (list[Territory]
                                   | list[Actor]
                                   | list[Product]
                                   | list[Gateflow]
                                   | list[Pathflow]
                                   | list[Stock]
                                   | int
                                   | Select):
        """Trouve les MTobjects correspondants aux identifiants.

        Args:
            type_mtobject: Type du MTObject (parmis Territory, Actor, Product, Gateflow, Pathflow, Stock)
            ids: Liste des identifiants.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des acteurs.
                * `count`: Nombre d'éléments correspondants.
            verbose:

        Returns:
            (list[MTObject]): Liste des objets correspondants.
            (int): Nombre d'objets correspondants aux identifiants.
            (Select): Requète des objects ou des identifiants.
        """
        if isinstance(ids, int):
            ids = {ids}

        q = {}
        for nq, targetq in zip(["id", "object"], [type_mtobject.id, type_mtobject]):
            q[nq] = select(targetq).where(type_mtobject.id.in_(ids))

        result = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return result

    def get_mtobjects_tap_in(self,
                             mtobject: (Territory | Actor | Product |
                                        list[Territory] | list[Actor] |
                                        list[Product] | int),
                             returnmtobjecttype: (Literal['territory',
                                                          'actor',
                                                          'product']
                                                  | type[Territory,
                                                         Actor,
                                                         Product]),
                             scale: str | None = None,
                             sourceref: str | None = None,
                             self_include: bool = False,
                             cache_properties: list[str] = [],
                             return_type: Literal['list', 'object',
                                                  'id', 'queryid', 'qid',
                                                  'query', 'count'] = 'list',
                             verbose: bool = False
                             ) -> (list[Territory] | list[Actor] | list[Product] |
                                   list[int] | Select | int):
        if verbose:
            print(f"-------- GET MTOBJECT IN | {type(mtobject)=}")

        if type(returnmtobjecttype) is str:
            returnmtobjecttype = SidbStatic.get_mtobjecttype_from_classname(returnmtobjecttype)

        if returnmtobjecttype not in [Actor, Territory, Product]:
            raise TypeError("'%s' is unsupported type" % returnmtobjecttype)

        if sourceref is not None:
            raise ValueError("'sourceref' argument is not defined yet. #Todo")

        if isinstance(mtobject, (Territory, Actor, Product)):
            id_start = mtobject.id
            type_mtobject = type(mtobject)
        elif isinstance(mtobject, int):
            id_start = mtobject
            type_mtobject = returnmtobjecttype
        elif isinstance(mtobject, (list, tuple)):
            if isinstance(mtobject[0], int):
                id_start = mtobject
                type_mtobject = returnmtobjecttype
            else:
                type_mtobject = type(mtobject[0])
                id_start = [mto.id for mto in mtobject]
        else:
            raise TypeError(f"Unexpected 'mtobject' type: {type(mtobject)}")

        if type_mtobject is returnmtobjecttype:  # Même type objet initial et cible
            if verbose:
                print(f"----------- CASE type(mtobject) == returnmtobjecttype == {type(mtobject)}")
            subquery = SidbStatic.subquery_recursive(returnmtobjecttype,
                                                     [returnmtobjecttype.id], id_start,
                                                     f"IsIn{returnmtobjecttype.__name__}")
            if verbose:
                print(f"Used in-key : IsIn{returnmtobjecttype.__name__}")
            q = {}
            for nq, targetq in zip(["id", "object"], [returnmtobjecttype.id, returnmtobjecttype]):
                q[nq] = select(targetq).join(subquery)
                if scale is not None:
                    q[nq] = q[nq].join(returnmtobjecttype.properties)
                    q[nq] = q[nq].where(Property.name_a == "Scale")
                    q[nq] = q[nq].where(Property.value_literal == scale)
                if not self_include:
                    q[nq] = q[nq].where(returnmtobjecttype.id != id_start)

        elif (type(mtobject) is Territory) and (returnmtobjecttype is Actor):
            if verbose:
                print("----------- CASE Actor in Territory")
            q = {}
            property1_alias = aliased(Property, name='property1_alias')
            for nq, targetq in zip(["id", "object"], [returnmtobjecttype.id, returnmtobjecttype]):
                mapid = self.get_mtobjects_tap_in(mtobject, Territory, return_type='qid')
                q[nq] = select(targetq)
                q[nq] = q[nq].join(property1_alias, returnmtobjecttype.properties)
                q[nq] = q[nq].where(property1_alias.name_a == "IsInTerritory")
                q[nq] = q[nq].where(property1_alias.value_mtobject_id.in_(mapid))

                if scale is not None:
                    property2_alias = aliased(Property, name='property2_alias')
                    q[nq] = q[nq].join(property2_alias, returnmtobjecttype.properties)
                    q[nq] = q[nq].where(property2_alias.name_a == "Scale")
                    q[nq] = q[nq].where(property2_alias.value_literal == scale)
        else:
            print()
            raise AttributeError("Distinct type are not defined yet [Initial_look_in = "
                                 f"{type(mtobject)}| return_type = {type(returnmtobjecttype)}]")

        returnval = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return returnval

    def get_mtobjects_tap_on(self,
                             mtobject: (Territory | Actor | Product |
                                        list[Territory] | list[Actor] |
                                        list[Product] | int),
                             mtobject_to_return: type[Territory, Actor, Product],
                             scale: str | None = None,
                             self_include: bool = False,
                             cache_properties: list[str] = [],
                             return_type: Literal['list', 'object',
                                                  'id', 'queryid', 'qid',
                                                  'query', 'count'] = 'list'
                             ) -> (list[Territory] | list[Actor] | list[Product] |
                                   list[int] | Select | int):
        if mtobject_to_return not in [Territory, Actor, Product]:
            raise TypeError("'mtobject_to_return' has to be Actor, Territory or "
                            f"Product, got '{mtobject_to_return}'.")

        if isinstance(mtobject, (Territory, Actor, Product)):
            id_start = mtobject.id
            type_mtobject = type(mtobject)
        elif isinstance(mtobject, int):
            id_start = mtobject.id
            type_mtobject = mtobject_to_return
        elif isinstance(mtobject, (list, tuple)):
            if isinstance(mtobject[0], int):
                id_start = mtobject
                type_mtobject = mtobject_to_return
            else:
                type_mtobject = type(mtobject[0])
                id_start = [mto.id for mto in mtobject]
        else:
            raise TypeError(f"Unexpected 'mtobject' type : {type(mtobject)}")

        subq = SidbStatic.subquery_recursive_reverse(mtobject_to_return,
                                                     [mtobject_to_return.id], id_start,
                                                     f"IsIn{mtobject_to_return.__name__}")
        q = {}
        for nq, targetq in zip(["id", "object"], [mtobject_to_return.id, mtobject_to_return]):
            q[nq] = select(targetq).join(subq)
            if scale is not None:
                q[nq] = (q[nq].join(mtobject_to_return.properties)
                         .where(Property.name_a == "Scale")
                         .where(Property.value_literal == scale))
            if not self_include:
                if isinstance(id_start, int):
                    q[nq] = q[nq].where(mtobject_to_return.id != id_start)
                else:
                    q[nq] = q[nq].where(~mtobject_to_return.id.in_(id_start))

        result = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return result

    def get_mtobjects_gs(self,
                         object_class: type[Gateflow, Stock],
                         target: list[Territory | Actor] = [],
                         flowtype: str | None = None,
                         product: Product | Iterable[Product] | None = None,
                         product_asc: bool = False,
                         product_desc: bool = True,
                         date_point: str | date | None = None,
                         date_start: str | date | None = None,
                         date_end: str | date | None = None,
                         year: str | int | None = None,
                         month: str | int | None = None,
                         sourceref: str | None = None,
                         filter_by: list[tuple[str, str]] = [],
                         use_or: bool = True,
                         map_id: Iterable[int] | int | Select = [],
                         cache_properties: list[str] = [],
                         return_type: Literal['list', 'object',
                                              'id', 'queryid', 'qid',
                                              'query', 'count'] = 'list',
                         verbose: bool = False
                         ) -> list[Gateflow] | list[Stock] | list[int] | int | Select:
        """
        FutureDev:
            - Implementer target_(asc/desc).
        """
        date_point = to_date(date_point)
        date_start, date_end = get_start_end_dates(start=date_start, end=date_end,
                                                   year=year, month=month)
        if date_point and (date_start or date_end):
            raise ValueError("Invalid date arguments: date_point and a date range"
                             " is not compatible.")
        if verbose:
            print(f"{date_start=}/{date_end=}")

        q = {}
        for nq, targetq in zip(["id", "object"], [object_class.id, object_class]):
            q[nq] = select(targetq)
            if sourceref is not None:
                q[nq] = (q[nq].join(object_class.properties)
                         .where(Property.sourceref == sourceref)
                         )
            if date_point:
                q[nq] = q[nq].where(or_(object_class.date_point == date_point,
                                        and_(object_class.date_start <= date_point,
                                             object_class.date_end >= date_point)))
            elif date_start != date.min or date_end != date.max:
                q[nq] = q[nq].where(or_(and_(object_class.date_start <= date_end,
                                             object_class.date_end >= date_start),
                                        and_(object_class.date_point <= date_end,
                                             object_class.date_point >= date_start)))

            if flowtype is not None and object_class is Gateflow:
                flowtype = flowtype.lower()
                q[nq] = q[nq].where(object_class.flowtype == flowtype)
            # Product search
            if product is not None:
                products_search = []
                if product_desc:
                    products_search.append(object_class.product_id.in_(
                        self.get_products_in(product, return_type="qid")
                        ))
                if product_asc:
                    products_search.append(object_class.product_id.in_(
                        self.get_products_on(product, return_type="qid")
                        ))
                if not products_search:
                    if isinstance(product, Product):
                        product = {product.id}
                    else:
                        product = {p.id for p in product}
                    products_search.append(object_class.product_id.in_(product))
                q[nq] = q[nq].where(or_(*products_search))
            if target:
                if isinstance(target, (Territory, Actor)):
                    target = [target]
                target_search = []
                for tg in target:
                    if type(tg) is Territory:
                        target_search.append(object_class.territory_id.in_(self.get_territories_in(tg, return_type="qid")))
                        target_search.append(object_class.actor_id.in_(self.get_actors_in(tg, return_type="qid")))
                    elif type(tg) is Actor:
                        target_search.append(object_class.actor_id.in_(self.get_actors_in(tg, return_type="qid")))
                    else:
                        raise TypeError(f"Unknown target type : '{type(tg)}' --> {tg}")
                if use_or:
                    q[nq] = q[nq].where(or_(*target_search))
                else:
                    q[nq] = q[nq].where(and_(*target_search))

            for name, value in filter_by:
                p = aliased(Property)
                name_a, *name_b = name.split('@', 1)
                q[nq] = (q[nq].join(p, object_class.properties)
                         .where(p.name_a == name_a))
                if name_b:
                    q[nq] = q[nq].where(p.name_b == name_b[0])
                if value != '*':
                    q[nq] = q[nq].where(p.value_literal == value)

            if map_id:
                if isinstance(map_id, int):
                    map_id = (map_id,)
                q[nq] = q[nq].where(object_class.id.in_(map_id))

        result = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return result

    def cache_mtobject_properties(self, mtobject: MTObject) -> list[Property]:
        """Met en cache les propriétés d'un MTObject"""
        return self.session.scalars(
            select(Property)
            .where(Property.item_id == mtobject.id)
        ).all()

    def get_one_mtobject_from_cache(self,
                                    mtobject_type: str,
                                    attribute_name: str,
                                    attribute_value: str,
                                    prefix: str = "") -> MTObject | None:
        """ ....
        Regarde le résultat d'une requête ce trouve dans le cache pour éviter
        de refaire la requête et gagner du temps. \n
        :param prefix: Use to add a prefix for cache search (product nomenclature)
        :type prefix: string (defaut = "")
        :return: L'objet en cache s'il existe, None sinon
        :rtype: MTObject / None
        """

        # Pour un produit dans le cache :
        # nom d'attribut = "Nomenclature/Code" ou "Nomenclature/Name"
        prefix = prefix + "/" if prefix else ''

        # Cas d'un code ou d'un nom précisé
        if attribute_name[0:5] in ["Name@", "Code@"]:
            temp_mtobject = self.get_cache(mtobject_type, prefix + attribute_name, attribute_value)
            if temp_mtobject is None:
                temp_mtobject = self.get_cache(mtobject_type,
                                               prefix + attribute_name[0:4] + "Alias"
                                               + attribute_name[4:],
                                               attribute_value)

        # Code ou nom, non précisé
        elif attribute_name in ["Code", "Name"]:
            temp_mtobject = self.get_cache(mtobject_type,
                                           prefix + attribute_name, attribute_value)
            if temp_mtobject is None:
                temp_mtobject = self.get_cache(mtobject_type,
                                               prefix + attribute_name + "_", attribute_value)
            if temp_mtobject is None:
                temp_mtobject = self.get_cache(mtobject_type,
                                               prefix + attribute_name + "Alias", attribute_value)
            if temp_mtobject is None:
                temp_mtobject = self.get_cache(mtobject_type,
                                               prefix + attribute_name + "Alias_", attribute_value)

        else:
            raise AttributeError(f"Unexpected cache key '{attribute_name}'={attribute_value}")
        return temp_mtobject

    def set_cache_mtobject_codename(self,
                                    mtobject: MTObject,
                                    attribute_name: str,
                                    attribute_value: str,
                                    use_alias: bool,
                                    prefix: str = "") -> None:
        """ Set mtobject in cache for Territory, Actor, Product
        """
        # Pour un produit dans le cache :
        # nom d'attribut = "Nomenclature/Code" ou "Nomenclature/Name"
        prefix = prefix + "/" if prefix else ''

        if attribute_name in ["Code", "Name"]:
            if not use_alias:
                self.set_cache(mtobject, prefix + attribute_name, attribute_value)
                self.set_cache(mtobject, prefix + attribute_name + "_", attribute_value)
            else:
                self.set_cache(mtobject, prefix + attribute_name + "Alias", attribute_value)
                self.set_cache(mtobject, prefix + attribute_name + "Alias_", attribute_value)
        else:
            # Exemple : attribute_name == "Code@insee"
            if not use_alias:
                self.set_cache(mtobject, prefix + attribute_name, attribute_value)
                self.set_cache(mtobject, prefix + attribute_name[0:4] + "_", attribute_value)
            else:
                self.set_cache(mtobject, prefix + attribute_name[0:4] + "Alias" + attribute_name[4:], attribute_value)
                self.set_cache(mtobject, prefix + attribute_name[0:4] + "Alias_", attribute_value)
