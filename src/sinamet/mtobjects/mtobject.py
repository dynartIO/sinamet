from __future__ import annotations

import warnings

from collections.abc import Iterable
from typing import Literal, overload, TYPE_CHECKING

from datetime import date

from anytree import Node

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import reconstructor

from sinamet.mtobjects.property import Property
from sinamet.mtobjects.dbobject import DBObjectClassBase
from sinamet.tools.timext import get_start_end_dates, to_date
from sinamet.tools.profile import Profile
from sinamet.errors import SidbMultiFoundError, SidbNotFoundError

if TYPE_CHECKING:
    from shapely import Geometry
    from sqlalchemy import Select
    from sinamet.mapper import Mapper
    from sinamet.mtobjects.actor import Actor


class MTObject(DBObjectClassBase):
    """
    Classe mère des objets du modèle de Sinamet : `Territory`, `Actor`, `Product`, `Gateflow`, `Pathflow`, `Stock`

    Parameters:
        properties: Liste des propriétés de l'objet
        type: type d'objet (parmis `territory`, `actor`, `product`, `gateflow`, `pathflow`, `stock`)
    """
    __tablename__ = 'mtobject'

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(25))

    properties: Mapped[list[Property]] = relationship(
            back_populates="item",
            primaryjoin=Property.item_id == id,
            cascade="all, delete-orphan")
    property_values: Mapped[list[Property]] = relationship(
            back_populates="value_mtobject",
            primaryjoin=Property.value_mtobject_id == id,
            cascade="all, delete-orphan")

    date_start: Mapped[date | None]
    date_end: Mapped[date | None]

    __mapper_args__ = {'polymorphic_identity': __tablename__,
                       'polymorphic_on': type}

    def __init__(self):
        self.properties = []
        self.cached_properties: dict[str, list[Property]] = {}

    @reconstructor
    def init_on_load(self) -> None:
        self.cached_properties: dict[str, list[Property]] = {}

    def __str__(self) -> str:
        return "<MTObject>"

    def __repr__(self) -> str:
        s = f'{self}\n'
        for property in self.properties:
            s += f'    > {property}\n'
        return s

    def to_string_object(self) -> str:
        mydict = self.get_codes(return_type="dict")
        mykey = list(mydict.keys())[0]
        mykey = "Code" if mykey == "_" else "Code@%s" % mykey
        return "%s(%s=%s)" % (self.__class__.__name__, mykey, list(mydict.values())[0])

    def __getattr__(self, attr):
        if attr == "name":
            return self.get_name()
        elif attr == "code":
            return self.get_code()
        else:
            raise AttributeError(f"Uknown attribute '{attr}'")

    def get_tree(self, verbose: bool = False) -> Node:
        """Crée la hiérarchie des produits contenus dans un produit.

        Parameters:
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.

        Returns:
            La Node principale de l'arbre hierarchisé.

        Raises:
            SidbMultiFoundError: Si un produit a plusieurs parents.
        """
        from sinamet.sidb import Sidb
        root_node = Node(self.get_name(force_cache=True), mtobject=self)
        node_dict = {self.id: root_node}
        lst_object_children = (Sidb.get_sidb_from_object(self)
                               .get_products_in(self, "list", cache_properties=["IsInProduct"]))
        if verbose:
            print(f"Got {len(lst_object_children)} objects.")
        for child in lst_object_children:
            _parent = child.get_property("IsInProduct")
            if type(_parent) is list:
                [print(f"{pr=}") for pr in _parent]
                raise SidbMultiFoundError(f"Multi parents found in nomenclature for {child}")
            if child.id not in node_dict:
                _child_node = Node(child.get_name(force_cache=True), mtobject=child)
                node_dict[child.id] = _child_node
            else:
                _child_node = node_dict[child.id]
            if _parent is not None:
                if _parent.id not in node_dict:
                    _parent_node = Node(_parent.get_name(force_cache=True), mtobject=_parent)
                    node_dict[_parent.id] = _parent_node
                else:
                    _parent_node = node_dict[_parent.id]
                _child_node.parent = _parent_node
        return root_node

    def get_property_gen(
            self,
            prop_name: str,
            prop_type: Iterable[str] | str = [],
            /, *,
            date_point: str | date | None = None,
            return_type: Literal['value', 'property', 'tuple'] = "value",
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            if_many: Literal['raise', 'warn_first', 'warn_list',
                             'first', 'list'] = "warn_first",
            verbose: bool = False
            ) -> (str | int | float | MTObject | Geometry | Property | None |
                  tuple[str | int | float | MTObject | Geometry, str] |
                  list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]]):
        """Fonction qui renvoie la ou les propriétés correspondantes aux arguments.

        Examples:
            >>> charente = get_territory("Name", "Charente")
            >>> charente.get_property_gen("Population", date_point="01/01/2023")
            351036.0
            >>> charente.get_property_gen("Name", ["fr", "en"]) or "-"  # `or` pour gérer une valeur par défaut

        Parameters:
            prop_name: Nom de la propriété.
            prop_type: Si précisé recherche une propriété avec la précision donnée.
                Sinon, recherche une propriété sans précision.
            date_point: Dâte de la propriété recherchée.
            return_type (str): Type de retour de la fonction. Valeurs possibles:

                * `value`: La valeur uniquement (ex. "FR").
                * `property`: L'object propriété (ex. <Property:Name>).
                * `tuple`: Un tuple avec comme premier élément la valeur, et en
                    deuxième le type de la propriété (ex. ("FR", "isoa2")).
            if_none: Comportement en cas de propriété non trouvée: lève un erreur
                (`raise`), affiche un avertissement (`warn`) ou renvoie None (défaut).
            use_default: Si prop_type pas trouvé, renvoie la première propriété
                correspondant à prop_name.
            force_cache: Ne refait pas d'appel à la base de donnée et utilise les
                propriétés déjà mise en cache.
            if_many (str): Comportement en cas de plusieurs propriétés correspondantes
                au même nom ou code. Valeurs possibles:

                * `raise`: Lève une erreur.
                * `warn_first`: Avertit puis renvoie la première valeur.
                * `warn_list`: Avertit puis renvoie la liste.
                * `first`: Renvoie la première valeur.
                * `list`: Renvoie la liste.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.

        Returns:
            (str | int | float | MTObject | Geometry): La valeur de la propriété.
            (Property): L'object Property lui-même.
            (tuple[str | int | float | MTObject | Geometry, str]): Le tuple contenant la valeur
                de la propriété et la précision de la propriété.
            (None): Aucune propriété n'a été trouvée.

        Raises:
            ValueError: Si la valeur de `return_type` ou `if_many` est incorrecte.
            SidbNotFoundError: Si aucune propriété n'a été trouvée et que
                `if_none == 'raise'`.
            SidbMultiFoundError: Si plusieurs propriétés correspondent et que
                `if_many == 'raise'`.

        Warns:
            UserWarning: Plusieurs propriétés correspondantes et `if_many` est
                `warn_first` ou `warn_list`.
        """
        from sinamet.sidb import Sidb

        if return_type not in (_list := ["tuple", "value", "property"]):
            raise ValueError(f"Argument `return_type` can only be one of {_list}, got '{return_type}'")
        if if_many not in (_list := ["raise", "warn_first", "warn_list", "first", "list"]):
            raise ValueError(f"Argument `if_many` can only be one of {_list}, got '{if_many}'")

        # Vérification dans le cache
        key_list = [key for key in self.cached_properties.keys() if key == prop_name
                    or key.startswith(prop_name + '@')]  # Tous ou aucun des codes chargés
        if verbose:
            print(f"Cache {key_list=}")
            print("Cached properties = ", self.cached_properties.keys())
        if not key_list and not force_cache:  # Rien dans le cache, chargement des propriétés
            Sidb.get_sidb_from_object(self).cache_mtobject_properties(self)
            key_list = [key for key in self.cached_properties.keys() if key == prop_name
                        or key.startswith(prop_name + '@')]
        if verbose:
            print(f"Non-cache {key_list=}")

        properties = (None, None)
        if type(prop_type) is str:
            prop_type = [prop_type]
        for type_ in prop_type:
            prop_full_name = prop_name
            if type_ != "_":
                prop_full_name += f"@{type_}"
            p = self.cached_properties.get(prop_full_name)
            if p:
                properties = (p, type_)
                break
        if not prop_type and prop_name in key_list:
            properties = (self.cached_properties[prop_name], '_')
        if not properties[0] and key_list and (use_default or not prop_type):
            _, _, key_b = key_list[0].partition('@')
            properties = (self.cached_properties[key_list[0]], key_b if key_b else '_')
        if verbose:
            print(f"{properties=}")

        if properties[0] and date_point:
            date_point = to_date(date_point)
            properties = ([p for p in properties[0] if (
                    p.date_point == date_point or
                    ((p.date_start and p.date_start <= date_point) and
                     (p.date_end and p.date_end >= date_point)) or
                    ((p.date_start and p.date_start <= date_point) and
                     not p.date_end) or
                    ((p.date_end and p.date_end >= date_point) and
                     not p.date_start)
                )], properties[1])

        if not (properties[0] and properties[1]):
            if if_none == 'raise':
                raise SidbNotFoundError(f"No such property has been found `{prop_name}"
                                        f"{'' if not prop_type else (f'@{prop_type}')}`.")
            elif if_none == 'warn':
                warnings.warn(f"No such property has been found `{prop_name}"
                              f"{'' if not prop_type else (f'@{prop_type}')}`.")
            return None

        match return_type:
            case 'value':
                properties = [v.get_value() for v in properties[0]]
            case 'property':
                properties = [p for p in properties[0]]
            case 'tuple':
                properties = [(p.get_value(), properties[1]) for p in properties[0]]

        if len(properties) == 1:
            return properties[0]
        match if_many:
            case "raise":
                raise SidbMultiFoundError(f"Several properties corresponding to {prop_name}"
                                          f"{'' if not prop_type else f'@{prop_type}'}.")
            case "warn_first":
                warnings.warn(f"Several properties corresponding to {prop_name}"
                              f"{'' if not prop_type else f'@{prop_type}'}, returning first.")
                return properties[0]
            case "warn_list":
                warnings.warn(f"Several properties corresponding to {prop_name}"
                              f"{'' if not prop_type else f'@{prop_type}'}, returning all.")
                return properties
            case "first":
                return properties[0]
            case "list":
                return properties

    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> str | int | float | MTObject | Geometry: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (str | int | float | MTObject | Geometry | list[str | int | float | MTObject | Geometry]): ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> str | int | float | MTObject | Geometry | None: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (str | int | float | MTObject | Geometry | None | list[str | int | float | MTObject | Geometry]): ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> Property: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> Property | list[Property]: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> Property | None: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> Property | list[Property] | None: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> tuple[str | int | float | MTObject | Geometry, str]: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (tuple[str | int | float | MTObject | Geometry, str] | list[tuple[str | int | float | MTObject | Geometry, str]]): ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> tuple[str | int | float | MTObject | Geometry, str] | None: ...
    @overload
    def get_code(self, codes: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (tuple[str | int | float | MTObject | Geometry, str] | None | list[tuple[str | int | float | MTObject | Geometry, str]]): ...

    def get_code(
            self,
            codes: Iterable[str] | str = [],
            /, *,
            date_point: str | date | None = None,
            return_type: Literal['value', 'property', 'tuple'] = "value",
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            if_many: Literal['raise', 'warn_first', 'warn_list',
                             'first', 'list'] = 'first',
            verbose: bool = False
            ) -> (str | int | float | MTObject | Geometry | Property | None |
                  tuple[str | int | float | MTObject | Geometry, str] |
                  list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]]):
        """Renvoie le code recherché.

        Fonction wrapper de [get_property_gen]
        [mtobjects.mtobject.MTObject.get_property_gen], avec `prop_name='Code'`
        """
        return self.get_property_gen("Code", codes, return_type=return_type,
                                     if_none=if_none, use_default=use_default,
                                     force_cache=force_cache, if_many=if_many,
                                     date_point=date_point, verbose=verbose)

    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> str | int | float | MTObject | Geometry: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (str | int | float | MTObject | Geometry | list[str | int | float | MTObject | Geometry]): ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> str | int | float | MTObject | Geometry | None: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (str | int | float | MTObject | Geometry | None | list[str | int | float | MTObject | Geometry]): ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> Property: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> Property | list[Property]: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> Property | None: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> Property | list[Property] | None: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> tuple[str | int | float | MTObject | Geometry, str]: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (tuple[str | int | float | MTObject | Geometry, str] | list[tuple[str | int | float | MTObject | Geometry, str]]): ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> tuple[str | int | float | MTObject | Geometry, str] | None: ...
    @overload
    def get_name(self, names: Iterable[str] | str = [], /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (tuple[str | int | float | MTObject | Geometry, str] | None | list[tuple[str | int | float | MTObject | Geometry, str]]): ...

    def get_name(
            self,
            names: Iterable[str] | str = [],
            /, *,
            date_point: str | date | None = None,
            return_type: Literal['value', 'property', 'tuple'] = "value",
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            if_many: Literal['raise', 'warn_first', 'warn_list',
                             'first', 'list'] = 'first',
            verbose: bool = False
            ) -> (str | int | float | MTObject | Geometry | Property | None |
                  tuple[str | int | float | MTObject | Geometry, str] |
                  list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]]):
        """Renvoie le nom recherché.

        Fonction wrapper de [get_property_gen]
        [mtobjects.mtobject.MTObject.get_property_gen], avec `prop_name='Name'`
        """
        return self.get_property_gen("Name", names, return_type=return_type,
                                     if_none=if_none, use_default=use_default,
                                     force_cache=force_cache, if_many=if_many,
                                     date_point=date_point, verbose=verbose)

    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> str | int | float | MTObject | Geometry: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (str | int | float | MTObject | Geometry | list[str | int | float | MTObject | Geometry]): ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> str | int | float | MTObject | Geometry | None: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (str | int | float | MTObject | Geometry | None | list[str | int | float | MTObject | Geometry]): ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> Property: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> Property | list[Property]: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> Property | None: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['property'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> Property | list[Property] | None: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> tuple[str | int | float | MTObject | Geometry, str]: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise'], use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (tuple[str | int | float | MTObject | Geometry, str] | list[tuple[str | int | float | MTObject | Geometry, str]]): ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['raise', 'warn_first', 'first'] = 'first', verbose: bool = False) -> tuple[str | int | float | MTObject | Geometry, str] | None: ...
    @overload
    def get_property(self, full_name: str, /, *, date_point: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['warn', None] = None, use_default: bool = False, force_cache: bool = False, if_many: Literal['warn_list', 'list'], verbose: bool = False) -> (tuple[str | int | float | MTObject | Geometry, str] | None | list[tuple[str | int | float | MTObject | Geometry, str]]): ...

    def get_property(
            self,
            full_name: str,
            /, *,
            date_point: str | date | None = None,
            return_type: Literal['value', 'property', 'tuple'] = "value",
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            if_many: Literal['raise', 'warn_first', 'warn_list',
                             'first', 'list'] = 'warn_first',
            verbose: bool = False
            ) -> (str | int | float | MTObject | Geometry | Property | None |
                  tuple[str | int | float | MTObject | Geometry, str] |
                  list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]]):
        """Renvoie la propriété recherchée.

        Fonction wrapper de [get_property_gen]
        [mtobjects.mtobject.MTObject.get_property_gen], prenant le nom complet
        de la propriété recherchée.
        """
        name_a, *name_b = full_name.split('@')
        return self.get_property_gen(name_a, name_b, return_type=return_type,
                                     if_none=if_none, use_default=use_default,
                                     force_cache=force_cache, if_many=if_many,
                                     date_point=date_point, verbose=verbose)

    def get_properties_gen(
            self,
            prop_name: str,
            prop_types: Iterable[str] = [],
            date_point: str | date | None = None,
            date_start: str | date | None = None,
            date_end: str | date | None = None,
            return_type: Literal['value', 'property',
                                 'tuple', 'dict',
                                 'profile'] = 'value',
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            verbose: bool = False
            ) -> (list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]] |
                  dict[str, str | int | float | MTObject | Geometry] | Profile):
        """Fonction qui renvoie les propriétés correspondantes aux arguments.

        Examples:
            >>> france = get_territory("Name", "France")
            >>> france.get_properties_gen("Code", ["isoa2", "isoa3"])
            ["FR", "FRA"]

        Parameters:
            prop_name: Nom de la propriété.
            prop_types: Si précisé recherche les propriétés avec les précision données.
                Sinon, recherche toutes les propriétés.
            return_type (str): Type de retour de la fonction. Valeurs possibles:

                * `value`: Les valeurs uniquement (ex. ["FR", "FRA"]).
                * `property`: Les objects `Property` (ex. [<Property:Name>, <Property:Name>]).
                * `tuple`: Une liste de tuples avec comme premier élément la valeur, et en deuxième
                    le type de la propriété (ex. [("FR", "isoa2"), ("FRA", "isoa3")]).
                * `dict`: Un dictionnaire (ex. {"isoa2": "FR", "isoa3": "FRA"}). Attention si
                    une précision comporte plusieurs propriétés.
                * `profile`: L'object `Profile` contenant les propriétés recherchées.
            if_none: Comportement en cas de propriété non trouvée: lève un erreur
                (`raise`), affiche un avertissement (`warn`) ou renvoie une liste vide (défaut).
            use_default: Renvoie toutes les propriétés en commençant par celles indiquées dans `prop_type`.
            force_cache: Ne refait pas d'appel à la base de donnée et utilise les
                propriétés déjà mise en cache.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.

        Returns:
            (list[str | int | float | MTObject | Geometry]): La liste des valeurs
                des propriétés recherchées.
            (list[Property]): La liste des objects `Property` recherchés.
            (list[tuple[str | int | float | MTObject | Geometry], str]): La liste des tuples
                contenants les valeurs des propriétés et leurs précisions.
            (dict[str, str | int | float | MTObject, Geometry]): Un dictionnaire avec comme clés
                les précisions des propriétés, et comme valeurs leurs valeurs.
            (Profile): L'object `Profile` contenant les propriétés recherchées.

        Raises:
            ValueError: Si la valeur de `return_type` est incorrecte.
            SidbNotFoundError: Si aucune propriété n'a été trouvée et que
                `if_none == 'raise'`.
        """
        from sinamet.sidb import Sidb

        if return_type not in (_list := ["tuple", "value", "property", "dict", "profile"]):
            raise ValueError(f"Argument `return_type` can only be one of {_list}, got '{return_type}'")

        # Vérification dans le cache
        key_list = [key for key in self.cached_properties.keys() if key == prop_name
                    or key.startswith(prop_name + '@')]  # Tous ou aucun des codes chargés
        if not key_list and not force_cache:  # Rien dans le cache, chargement des propriétés
            Sidb.get_sidb_from_object(self).cache_mtobject_properties(self)
            key_list = [key for key in self.cached_properties.keys() if key == prop_name
                        or key.startswith(prop_name + '@')]
        if verbose:
            print(f"{self.cached_properties=}")

        properties: list[tuple[Property, str]] = []
        for prop_type in prop_types:
            prop_full_name = prop_name
            if prop_type != "_":
                prop_full_name += f"@{prop_type}"
            _list = self.cached_properties.get(prop_full_name, [])
            if not _list:
                if if_none == 'raise':
                    raise SidbNotFoundError(f"No such property has been found `{prop_full_name}`.")
                elif if_none == 'warn':
                    warnings.warn(f"No such property has been found `{prop_full_name}`.")
            for p in _list:
                properties.append((p, prop_type))
        if not prop_types or use_default:
            for key in key_list:
                key_a, *key_b = key.split('@', 1)
                if ((key_b and key_b[0] in prop_types)
                   or (not key_b and "_" in prop_types)):
                    continue
                for p in self.cached_properties.get(key, []):
                    properties.append((p, key_b[0] if key_b else '_'))
        if properties and (date_point or date_start or date_end):
            properties = [p for p in properties
                          if _check_property_date(p[0], date_point, date_start, date_end)]

        if verbose:
            print(f"{properties=}")
        if not properties:
            if if_none == 'raise':
                raise SidbNotFoundError(f"No such properties have been found `{prop_name}"
                                        f"{'' if not prop_types else (f'@{prop_types}')}`.")
            elif if_none == 'warn':
                warnings.warn(f"No such properties have been found `{prop_name}"
                              f"{'' if not prop_types else (f'@{prop_types}')}`.")
            return []

        match return_type:
            case 'value': return [p[0].get_value() for p in properties]
            case 'property': return [p[0] for p in properties]
            case 'tuple': return [(p[0].get_value(), p[1]) for p in properties]
            case 'dict': return {p[1]: p[0].get_value() for p in properties}
            case 'profile': return Profile(properties=[p[0] for p in properties])

    @overload
    def get_codes(self, codes: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[str | int | float | MTObject | Geometry]: ...
    @overload
    def get_codes(self, codes: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[Property]: ...
    @overload
    def get_codes(self, codes: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[tuple[str | int | float | MTObject | Geometry, str]]: ...
    @overload
    def get_codes(self, codes: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['dict'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> dict[str, str | int | float | MTObject | Geometry]: ...
    @overload
    def get_codes(self, codes: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['profile'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> Profile: ...

    def get_codes(
            self,
            codes: Iterable[str] = [],
            /, *,
            date_point: str | date | None = None,
            date_start: str | date | None = None,
            date_end: str | date | None = None,
            return_type: Literal['value', 'property',
                                 'tuple', 'dict',
                                 'profile'] = 'value',
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            verbose: bool = False
            ) -> (list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]] |
                  dict[str, str | int | float | MTObject | Geometry] | Profile):
        """Renvoie les codes recherchés.

        Fonction wrapper de [get_properties_gen]
        [mtobjects.mtobject.MTObject.get_properties_gen], avec `prop_name='Code'`
        """
        return self.get_properties_gen("Code", codes, return_type=return_type,
                                       if_none=if_none, use_default=use_default,
                                       force_cache=force_cache, date_point=date_point,
                                       date_start=date_start, date_end=date_end,
                                       verbose=verbose)

    @overload
    def get_names(self, names: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[str | int | float | MTObject | Geometry]: ...
    @overload
    def get_names(self, names: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[Property]: ...
    @overload
    def get_names(self, names: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[tuple[str | int | float | MTObject | Geometry, str]]: ...
    @overload
    def get_names(self, names: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['dict'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> dict[str, str | int | float | MTObject | Geometry]: ...
    @overload
    def get_names(self, names: Iterable[str] = [], /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['profile'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> Profile: ...

    def get_names(
            self,
            names: Iterable[str] = [],
            /, *,
            date_point: str | date | None = None,
            date_start: str | date | None = None,
            date_end: str | date | None = None,
            return_type: Literal['value', 'property',
                                 'tuple', 'dict',
                                 'profile'] = 'value',
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            verbose: bool = False
            ) -> (list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]] |
                  dict[str, str | int | float | MTObject | Geometry] | Profile):
        """Renvoie les noms recherchés.

        Fonction wrapper de [get_properties_gen]
            [mtobjects.mtobject.MTObject.get_properties_gen], avec `prop_name='Code'`
        """
        return self.get_properties_gen("Name", names, return_type=return_type,
                                       if_none=if_none, use_default=use_default,
                                       force_cache=force_cache, date_point=date_point,
                                       date_start=date_start, date_end=date_end,
                                       verbose=verbose)

    @overload
    def get_properties(self, full_name: str, /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['value'] = 'value', if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[str | int | float | MTObject | Geometry]: ...
    @overload
    def get_properties(self, full_name: str, /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['property'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[Property]: ...
    @overload
    def get_properties(self, full_name: str, /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['tuple'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> list[tuple[str | int | float | MTObject | Geometry, str]]: ...
    @overload
    def get_properties(self, full_name: str, /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['dict'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> dict[str, str | int | float | MTObject | Geometry]: ...
    @overload
    def get_properties(self, full_name: str, /, *, date_point: str | date | None = None, date_start: str | date | None = None, date_end: str | date | None = None, return_type: Literal['profile'], if_none: Literal['raise', 'warn', None] = None, use_default: bool = False, force_cache: bool = False, verbose: bool = False) -> Profile: ...

    def get_properties(
            self,
            full_name: str,
            /, *,
            date_point: str | date | None = None,
            date_start: str | date | None = None,
            date_end: str | date | None = None,
            return_type: Literal['value', 'property',
                                 'tuple', 'dict',
                                 'profile'] = 'value',
            if_none: Literal['raise', 'warn', None] = None,
            use_default: bool = False,
            force_cache: bool = False,
            verbose: bool = False
            ) -> (list[str | int | float | MTObject | Geometry] | list[Property] |
                  list[tuple[str | int | float | MTObject | Geometry, str]] |
                  dict[str, str | int | float | MTObject | Geometry] | Profile):
        """Renvoie les propriétés recherchées.

        Fonction wrapper de [get_properties_gen]
        [mtobjects.mtobject.MTObject.get_properties_gen], prenant le nom complet
        des propriétés recherchées.
        """
        name_a, *name_b = full_name.split('@')
        return self.get_properties_gen(name_a, name_b, return_type=return_type,
                                       if_none=if_none, use_default=use_default,
                                       force_cache=force_cache, date_point=date_point,
                                       date_start=date_start, date_end=date_end,
                                       verbose=verbose)

    def delete_cached_properties(self) -> None:
        """Reset le dictionnaire des propriétés mises en cache."""
        self.cached_properties = {}

    def get_source_ref(self, *, force_cache: bool = False) -> str:
        """Renvoie les sources des propriétés de l'object.

        Parameters:
            force_cache: Si `True`, n'utilise que les propriétés déjà présentes
                en cache.

        Returns:
            La liste des sources des propriétés de l'object, en chaîne de
                caractères, séparées par des virgules.
        """
        from sinamet.sidb import Sidb
        if not force_cache:
            Sidb.get_sidb_from_object(self).cache_mtobject_properties(self)

        source_refs = set()
        for prop_list in self.cached_properties.values():
            for p in prop_list:
                source_refs.add(p.source_ref)
        return ",".join(source_refs)

    def get_children(self, depth: int = 1) -> list[MTObject]:
        """Renvoie les enfants de l'object.

        Parameters:
            depth: Profondeur maximale de recherche.

        Returns:
            La liste des enfants de l'object.
        """
        from sinamet.sidb import Sidb

        if depth == 1:
            return Sidb.get_mtobject_children(self)
        else:
            temp = []
            for child in Sidb.get_mtobject_children(self):
                temp += child.get_children(depth=depth-1)
            return temp

    def is_in(self, mtobject: MTObject, force_cache: bool = False, include_self=True) -> bool:
        """Détermine si un autre objet est contenu dans cet objet.

        Parameters:
            mtobject: L'objet dont on veut vérifier s'il se trouve dans cet objet.
            force_cache: Si `True`, utilise uniquement les propriétés mises en
                cache, et ne fait pas de requète sur la base de données.

        Returns:
            `True` si l'objet `mtobject` est contenu dans cet objet, `False` sinon.
        """
        from sinamet import Sidb

        if type(self) is not type(mtobject):
            raise TypeError("Different object types not implemented yet.")

        if (self == mtobject) and include_self:
            return True

        # Checking cache before querying
        cached_parents = [prop.get_value() for prop in self.cached_properties.get(f"IsIn{mtobject.__class__.__name__}", [])]

        if mtobject in cached_parents:
            return True
        for parent in cached_parents:
            if parent.is_in(mtobject, force_cache=True):
                return True
        if force_cache:
            return False

        # Nothing found in cache: querying...
        parents_id = (Sidb.get_sidb_from_object(self)
                      .get_mtobjects_tap_on(self, type(self),
                                            include_self=False,
                                            return_type="id"))
        return mtobject.id in parents_id

    def get_actors_in(self, scale: str | None = None,
                      include_self: bool = True,
                      cache_properties: list[str] = [],
                      return_type: Literal['list', 'object', 'id',
                                           'queryid', 'qid', 'query',
                                           'count'] = 'list',
                      verbose: bool = False) -> list[Actor] | list[int] | int | Select:
        """Renvoie les acteurs contenus dans cet objet (Territory ou Actor).

        Parameters:
            scale: L'échelle des acteurs recherchés.
            include_self: Si `True` et si `self` est un acteur, l'inclure dans la
                liste renvoyée.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.

        Returns:
            (list[MTobject]): Liste des acteurs contenus dans cet objet.
            (list[int]): List des identifiants des acteurs contenus dans cet objet.
            (int): Nombre d'acteurs contenus dans cet objet.
            (Select): Requète des acteurs ou des identifiants.
        """
        from sinamet.sidb import Sidb
        return (Sidb.get_sidb_from_object(self)
                .get_actors_in(self, scale=scale, include_self=include_self,
                               cache_properties=cache_properties,
                               return_type=return_type, verbose=verbose))

    def create_property(self, name: str,
                        value: str | int | float | MTObject | Geometry,
                        source_ref: str | None = None,
                        date_start: str | date | None = None,
                        date_end: str | date | None = None,
                        date_point: str | date | None = None) -> Property:
        """Crée une propriété associée à cet objet.

        Parameters:
            name: Nom de la propriété.
            value: Valeur de la propriété.
            source_ref: La source de référence de la propriété.
            date_start: Date de départ.
            date_end: Date de fin.
            date_point: Date tout court.

        Returns:
            La propriété créée.
        """
        prop = Property(name, value, source_ref, date_start=date_start,
                        date_end=date_end, date_point=date_point)
        self.properties.append(prop)
        return prop

    def set_extra_properties(self, mapper: Mapper) -> None:
        """Ajout des propriétés non fonctionnelles.

        Ne s'occupe pas des clefs spécifiques

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Raises:
            ValueError: Si une propriété unique est déjà renseignée avec une valeur
                différente.
        """
        # Clefs spécifiques, ne sont pas traitées dans cette méthode
        specific_keys = ["IsInProductCode", "IsInProductName", "IsInProduct",
                         "IsInTerritoryCode", "IsInTerritoryName", "IsInTerritory",
                         "IsInActorCode", "IsInActorName", "IsInActor",
                         "TerritoryCode", "TerritoryName", "Territory",
                         "ProductCode", "ProductName", "Product", "ProductNomenclature",
                         "ActorCode", "ActorName", "Actor",
                         "Code", "Name", "CodeAlias", "NameAlias",
                         "FlowType", "Quantity", "Nomenclature",
                         "DateStart", "DateEnd", "DatePoint", "Year", "Month"]

        for i in range(len(mapper)):
            dic = mapper.get_dict_i(i)
            # Clefs spécifiques, ne sont pas traitées dans cette méthode
            if dic["key"] in specific_keys or dic["key"].split("@")[0] in specific_keys:
                continue
            if dic["unique"]:
                prop = self.get_property(dic["key"], return_type="property")
                if prop is not None:
                    print("GOT PROP = %s" % prop)
                    if prop.get_value() != dic["value"]:
                        raise ValueError("Duplicate unique attribute")
                    else:
                        continue
            self.create_property(dic["key"], dic["value"],
                                 dic["source_ref"],
                                 date_start=dic["date_start"],
                                 date_end=dic["date_end"],
                                 date_point=dic["date_point"])

    def set_name(self, mapper: Mapper) -> tuple[str, str | None, str | None]:
        """Définit le(s) nom(s) de l'object.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.
        """
        lst_key_index = mapper.get_keys_index("Name", startswith=True, alias=True)
        if not len(lst_key_index):
            return "NO_DATA", "Name", None
        for i in lst_key_index:
            dic = mapper.get_dict_i(i)
            if type(dic["value"]) is not str:
                return "WRONG_DATA_TYPE", "Name", dic["value"]
            if dic["unique"]:
                prop = self.get_property(dic["key"], return_type="property")
                if prop is not None:
                    if prop.get_value() != dic["value"]:
                        return "CONFLICTING_DATA", "Name", dic["value"]
                    else:
                        continue
            self.create_property(dic["key"], dic["value"], dic["source_ref"])
        return "OK", None, None

    def set_code(self, mapper: Mapper) -> tuple[str, str | None, str | None]:
        """Définit le(s) code(s) de l'object.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            * Implémenter temporalité des attributs.
            * Vérifier si Valeur déjà présente en attribut
            * Pour "Code" et "Code@...", conflit si valeurs existantes non identiques
        """
        # Récupération des clefs correspondants aux codes
        lst_key_index = mapper.get_keys_index("Code", startswith=True, alias=True)

        # Pas de clef code disponible
        if not len(lst_key_index):
            return "NO_DATA", "Code", None

        # Parcours des clefs récupérées correspondant à des codes
        for i in lst_key_index:
            # PAS D'ajout du Code si clef etrangère (= référence à objet existant)
            if mapper.is_foreign_key(i):
                continue
            dic = mapper.get_dict_i(i)
            if type(dic["value"]) is not str:
                return "WRONG_DATA_TYPE", "Code", dic["value"]

            # Continue if not exists
            if (dic["key"], dic["value"]) in [(p.get_name(), p.get_value()) for p in self.properties]:
                continue
            self.create_property(dic["key"], dic["value"], dic["source_ref"])
        return "OK", None, None

    def set_nomenclature(self, mapper: Mapper) -> tuple[str, str | None,
                                                        str | None]:
        """Définit la nomenclatue de l'objet. (Product uniquement)

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Enlever attribut direct, laisser seulement la propriété objet.
        """
        lst_ikeys = mapper.get_keys_index("Nomenclature", startswith=True)
        if not len(lst_ikeys):
            return "NO_DATA", "Nomenclature", None
        if len(lst_ikeys) > 1:
            return "AMBIGUOUS_DATA", "Nomenclature", str(lst_ikeys)
        dic_nom = mapper.get_dict_i(lst_ikeys[0])
        existing_property = self.get_property("Nomenclature",
                                              return_type="property")
        if existing_property is None or not dic_nom["unique"]:
            self.create_property("Nomenclature", dic_nom["value"], dic_nom["source_ref"])
            return "OK", None, None
        elif (type(existing_property) is list) and dic_nom["unique"]:
            return "DATA_UNCOHERENCE", "Nomenclature", str(existing_property)
        elif existing_property.get_value() == dic_nom["value"]:
            return "OK", None, None
        else:
            return ("CONFLICTING_DATA", "Nomenclature",
                    f"{existing_property.get_value()}//{dic_nom['value']}")

    def set_isin_territory(self, mapper: Mapper) -> tuple[str, str | None,
                                                          str | None]:
        """Définit les territoires parents de l'objet.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Gestion de la temporalité.
        """
        from sinamet.sidb import Sidb

        lst_index_key = mapper.get_keys_index("IsInTerritory", startswith=True)
        if not len(lst_index_key):
            return "NO_DATA", "IsInTerritory", None
        for key in lst_index_key:
            one_map = mapper.get_dict_i(key)
            one_map["key"] = one_map["key"].replace("IsInTerritory", "")
            return_territory = (Sidb.get_sidb_from_object(self)
                                .get_territory(one_map["key"],
                                               one_map["value"],
                                               if_many='first'))
            if return_territory is None:
                return "WRONG_DATA", "IsInTerritory", f"{one_map['key']}='{one_map['value']}'"
            self.create_property("IsInTerritory", return_territory, one_map["source_ref"])
        return "OK", None, None

    def set_isin_actor(self, mapper: Mapper) -> tuple[str, str | None,
                                                      str | None]:
        """Définit les acteurs parents de l'objet.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Gestion de la temporalité.
        """
        from sinamet.sidb import Sidb

        lst_index_key = mapper.get_keys_index("IsInActor", startswith=True)
        if not len(lst_index_key):
            return "NO_DATA", "IsInActor", None
        for key in lst_index_key:
            one_map = mapper.get_dict_i(key)
            one_map["key"] = one_map["key"].replace("IsInActor", "")
            return_actor = (Sidb.get_sidb_from_object(self)
                            .get_actor(one_map["key"],
                                       one_map["value"],
                                       if_many='first'))
            if return_actor is None:
                return "WRONG_DATA", "IsInActor", str(one_map)
            else:
                self.create_property("IsInActor", return_actor, one_map["source_ref"])
        return "OK", None, None

    def set_isin_product(self, mapper: Mapper) -> tuple[str, str | None,
                                                        str | None]:
        """Définit les produits parents du produit.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Implémenter seulement arguments complémentaires.
        """
        from sinamet.sidb import Sidb

        lst_index_key = mapper.get_keys_index("IsInProduct", startswith=True)
        if not len(lst_index_key):
            return "NO_DATA", "IsInProduct", None

        for key in lst_index_key:
            one_map = mapper.get_dict_i(key)
            one_map["key"] = one_map["key"].replace("IsInProduct", "")
            return_product = (Sidb.get_sidb_from_object(self)
                              .get_product(one_map["key"],
                                           one_map["value"],
                                           nomenclature=mapper.get("Nomenclature"),
                                           if_many='first'))
            if return_product is None:
                return "WRONG_DATA", "IsInProduct", f"{one_map['key']}='{one_map['value']}'"
            self.create_property("IsInProduct", return_product, one_map["source_ref"])
        return "OK", None, None

    def set_territory(self, mapper: Mapper) -> tuple[str, str | None, str | None]:
        """Definit le territoire de l'objet.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Gestion des erreurs (plusieurs territoires trouvés)
        """
        from sinamet.sidb import Sidb
        from sinamet.mtobjects.territory import Territory

        object_t = mapper.get("Territory")
        if object_t is not None and not isinstance(object_t, Territory):
            return "WRONG_DATA_TYPE", "Territory", str(object_t)

        for search in ["Code", "Name"]:
            if object_t is None:
                index = mapper.get_keys_index("Territory" + search,
                                              startswith=True, alias=True)
                if len(index) > 1:
                    return "WRONG_DATA_INFO", f"Too many Territory{search}", str(len(index))
                elif len(index) == 1:
                    dici = mapper.get_dict_i(index[0])
                    naming_case = dici["key"].replace("Territory", "")
                    object_t = Sidb.get_sidb_from_object(self).get_territory(naming_case, dici["value"])
                    if object_t is None:
                        return "WRONG_DATA_INFO", dici["key"], dici["value"]

        if object_t is None:
            return "NO_DATA", "Territory", None

        if self.territory is None:
            self.create_property("Territory", object_t, dici["source_ref"])
        self.territory = object_t
        return "OK", None, None

    def set_emitter_territory(self, mapper: Mapper
                              ) -> tuple[str, str | None, str | None]:
        """Définit le territoire émetteur du flux."""
        return self.set_emitter_receiver_territory_actor(mapper, "Emitter",
                                                         "Territory")

    def set_emitter_actor(self, mapper: Mapper
                          ) -> tuple[str, str | None, str | None]:
        """Définit l'acteur émetteur du flux."""
        return self.set_emitter_receiver_territory_actor(mapper, "Emitter",
                                                         "Actor")

    def set_receiver_territory(self, mapper: Mapper
                               ) -> tuple[str, str | None, str | None]:
        """Définit le territoire récepteur du flux."""
        return self.set_emitter_receiver_territory_actor(mapper, "Receiver",
                                                         "Territory")

    def set_receiver_actor(self, mapper: Mapper,
                           ) -> tuple[str, str | None, str | None]:
        """Définit l'acteur récepteur du flux."""
        return self.set_emitter_receiver_territory_actor(mapper, "Receiver",
                                                         "Actor")

    def set_emitter_receiver_territory_actor(self, mapper: Mapper,
                                             direction: Literal['Emitter', 'Receiver'],
                                             mtobjecttype: Literal['Actor', 'Territory'],
                                             ) -> tuple[str, str | None,
                                                        str | None]:
        """Définit les récepteurs ou émetteurs du flux.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.
            direction: Récepteur (Receiver) ou émetteur (Emitter).
            mtobjecttype: Le type: Territory ou Actor.

        Returns:
            Un tuple indiquant le résultat de l'opération.
        """
        from sinamet.sidb import Sidb
        from sinamet.mtobjects.actor import Actor
        from sinamet.mtobjects.territory import Territory

        if direction not in ['Emitter', 'Receiver']:
            raise ValueError('The direction can only be \'Emitter\' or \'Receiver\'')
        if mtobjecttype not in ['Actor', 'Territory']:
            raise ValueError('The mtobjecttype can only be \'Actor\' or \'Territory\'')

        object_t = mapper.get(direction + mtobjecttype)
        if object_t is not None:
            if object_t.__class__.__name__ != mtobjecttype:
                return "WRONG_DATA_TYPE", direction + mtobjecttype, str(object_t)
        search_cases = ["Code", "Name", "Id"]
        for sc in search_cases:
            if object_t is None:
                index = mapper.get_keys_index(direction + mtobjecttype + sc, startswith=True, alias=True)
                if len(index) > 1:
                    return "WRONG_DATA_INFO", direction + mtobjecttype + f":nb({sc})", str(len(index))
                elif len(index) == 1:
                    dici = mapper.get_dict_i(index[0])
                    naming_case = dici["key"].replace(direction + mtobjecttype, "")
                    object_t = (Sidb.get_sidb_from_object(self)
                                .get_mtobject_tap(Actor if mtobjecttype == 'Actor' else Territory,
                                                  naming_case, dici["value"]))
                    if object_t is None:
                        return "WRONG_DATA_INFO", dici["key"] + " ~ " + naming_case, dici["value"]

        if object_t is None:
            return "NO_DATA", direction + mtobjecttype, None

        setattr(self, f'{direction.lower()}_{mtobjecttype.lower()}', object_t)
        self.create_property(direction + mtobjecttype, object_t, mapper.all_srcref)
        return "OK", None, None

    def set_actor(self, mapper: Mapper,
                  verbose: bool = False) -> tuple[str, str | None,
                                                  str | None]:
        """Définit l'acteur lié à l'objet.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Gestion des erreurs (plusieurs produits trouvés)
        """
        from sinamet.sidb import Sidb

        if verbose:
            print("LOADED MAPPER = %s" % mapper)
        dic_object = mapper.get_dict_key("Actor")
        if verbose:
            print(dic_object)
        object_t = None
        if dic_object is not None:
            object_t = dic_object["value"]
            srcref_t = dic_object["source_ref"]
        else:
            # Pas de clef direct, recherche sur les noms / codes
            search_cases = ["Code", "Name"]
            for sc in search_cases:
                index = mapper.get_keys_index("Actor" + sc,
                                              startswith=True, alias=True)
                if verbose:
                    print("INDEX = %s" % index)
                if len(index) > 1:
                    return "WRONG_DATA_INFO", "Actor" + sc + ".nb()" % sc, len(index)
                elif len(index) == 1:
                    dici = mapper.get_dict_i(index[0])
                    naming_case = dici["key"].replace("Actor", "")
                    if verbose:
                        print("LOOKING FOR : %s = %s" % (naming_case, dici["value"]))
                    object_t = (Sidb.get_sidb_from_object(self)
                                .get_actor(naming_case, dici["value"]))
                    srcref_t = dici["source_ref"]
                    if object_t is None:
                        return "WRONG_DATA_INFO", dici["key"], dici["value"]

        if object_t is None:
            return "NO_DATA", "Actor", None
        elif object_t.__class__.__name__ != "Actor":
            return "WRONG_DATA_TYPE", "Actor", str(object_t)

        self.actor = object_t
        self.create_property("Actor", object_t, srcref_t)
        return "OK", None, None

    def set_flowtype(self, mapper: Mapper) -> tuple[str, str | None, str | None]:
        """Définit le type de flux.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.
        """
        flow_type = mapper.get_dict_key("FlowType")
        if flow_type is not None:
            self.flowtype = flow_type["value"].lower()
            self.create_property("FlowType", self.flowtype, flow_type["source_ref"])
        return "OK", None, None

    def set_product(self, mapper: Mapper) -> tuple[str, str | None, str | None]:
        """Définit le produit lié à l'objet.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Gestion des erreurs (plusieurs territoires trouvés)
        """
        from sinamet.sidb import Sidb

        dic_object = mapper.get_dict_key("Product")
        if dic_object is not None:
            object_t = dic_object["value"]
            srcref_t = dic_object["source_ref"]
        else:
            # Pas de clef direct, recherche sur les noms / codes
            search_cases = ["Code", "Name"]
            for sc in search_cases:
                nomencl = mapper.get("ProductNomenclature")
                index = mapper.get_keys_index("Product" + sc,
                                              startswith=True, alias=True)
                if len(index) > 1:
                    return "WRONG_DATA_INFO", "Product" + sc + ".nb()" % sc, str(len(index))
                elif len(index) == 1:
                    dici = mapper.get_dict_i(index[0])
                    naming_case = dici["key"].replace("Product", "")
                    object_t = (Sidb.get_sidb_from_object(self)
                                .get_product(naming_case, dici["value"],
                                             nomenclature=nomencl))
                    if object_t is None:
                        return "WRONG_DATA_INFO", dici["key"], dici["value"]
                    srcref_t = dici["source_ref"]

        if object_t is None:
            return "NO_DATA", "Product", None
        elif object_t.__class__.__name__ != "Product":
            return "WRONG_DATA_TYPE", "Product", str(object_t)

        self.product = object_t
        self.create_property("Product", object_t, srcref_t)
        return "OK", None, None

    def set_timeperiod(self, mapper: Mapper) -> tuple[str, str | None,
                                                      str | None]:
        """Définit la temporalité de l'objet.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.
        """
        year = mapper.get("Year")
        month = mapper.get("Month")
        start = mapper.get("DateStart")
        end = mapper.get("DateEnd")
        point = mapper.get("DatePoint")

        try:
            if point is not None:
                if start or end or year or month:
                    raise ValueError("Cannot have date_point with other date infos")
                self.date_point = to_date(point)
            start, end = get_start_end_dates(start=start, end=end,
                                             year=year, month=month)
            self.date_start = start
            self.date_end = end
            return "OK", None, None
        except ValueError as e:
            return "WRONG_DATA_TYPE", "Date", str(e)

    def set_quantity(self, mapper: Mapper) -> tuple[str, str | None, str | None]:
        """Définit la quantité de l'objet.

        Parameters:
            mapper: L'object `Mapper` lié à cet objet.

        Returns:
            Un tuple indiquant le résultat de l'opération.

        Note: FutureDev
            Implementer gestion temporalité des flux (actuellement lève erreur).
        """
        q_index = mapper.get_keys_index("Quantity", exact=False, startswith=True)
        for index in q_index:
            dici = mapper.get_dict_i(index)

            # Vérification de l'absence des clefs temporelles
            datekeys = ['date_start', 'date_end', 'date_point']
            for dk in datekeys:
                if dici[dk] is not None:
                    # Passage d'attribut temporel avec le "Quantity"
                    # WRONG_DATA_INFO => Incoherence
                    return "WRONG_DATA_INFO", dici["key"] + ":" + dk, dici[dk]

            # Extraction de l'unité
            try:
                unit = dici["key"].split("@")[1]
            except IndexError:
                # Problème sur la clef (= pas de @unit)
                # WRONG_DATA_NAME => Mauvais nom d'attribut
                return "WRONG_DATA_NAME", dici["key"], dici["value"]

            # Extraction et conversion de la valeur
            try:
                float_val = float(dici["value"])
            except ValueError:
                try:
                    float_val = float(dici["value"].replace(",", "."))
                except ValueError:
                    print("VALUE ERROR = '%s'" % dici["value"])
                    float_val = float('nan')
                # WRONG_DATA_TYPE => Mauvais type d'attribut

            # Paramétrage de l'objet & Ajout de l'attribut spécifique
            try:
                self.quantity = {unit: float_val, **self.quantity}
            except TypeError:
                raise AttributeError("Unknown error for self.quantity = %s with "
                                     "unit = '%s' or value = '%s'" % (self.quantity, unit, float_val))
            src_ref = dici["source_ref"]
            if src_ref is None:
                src_ref = mapper.get("SourceRef")

            self.create_property(dici["key"], float_val, src_ref)
        return "OK", None, None


def _check_property_date(
        p: Property,
        date_point: str | date | None,
        date_start: str | date | None,
        date_end: str | date | None
        ) -> bool:
    """Vérifie si la propriété `p` correspond aux critères de date.

    Parameters:
        p: La propriété à vérifier.
        date_point: La date ponctuelle.
        date_start: La date de début.
        date_end: La date de fin.

    Returns:
        `True` si la propriété correspond aux critères de date, `False` sinon.
    """
    if date_point and (date_end or date_start):
        raise ValueError("Invalid date arguments: date_point and a date range"
                         " is not compatible.")

    date_point = to_date(date_point)
    date_start = to_date(date_start)
    date_end = to_date(date_end)

    if date_start and date_end:
        return bool(
            (p.date_start and p.date_end
             and p.date_start <= date_end and p.date_end >= date_start) or
            (p.date_start and not p.date_end and p.date_start <= date_end) or
            (p.date_end and not p.date_start and p.date_end >= date_start) or
            (p.date_point and date_start <= p.date_point <= date_end))
    elif date_start:
        return bool(
            (p.date_start and not p.date_end) or
            (p.date_end and p.date_end >= date_start) or
            (p.date_point and p.date_point >= date_start))
    elif date_end:
        return bool(
            (p.date_end and not p.date_start) or
            (p.date_start and p.date_start <= date_end) or
            (p.date_point and p.date_point <= date_end))
    elif date_point:
        return bool(
            p.date_point == date_point or
            (p.date_start and p.date_end
             and p.date_start <= date_point <= p.date_end) or
            (p.date_start and not p.date_end and p.date_start <= date_point) or
            (p.date_end and not p.date_start and date_point <= p.date_end))
    return True
