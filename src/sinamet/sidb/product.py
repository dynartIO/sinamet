from typing import Literal, Iterable

from sqlalchemy import select
from sqlalchemy import Select

from sinamet.mtobjects.product import Product
from sinamet.mtobjects.property import Property
from sinamet.errors import SidbMultiFoundError
from sinamet.core.mapper import Mapper, MapperError


class SidbProduct:
    def get_product(self,
                    *args,
                    nomenclature: str | None = None,
                    like_value: bool = False,
                    case_value: bool = True,
                    accent_value: bool = True,
                    return_type: Literal['object',
                                         'id',
                                         'query',
                                         'queryid',
                                         'qid',
                                         ] = 'object',
                    raise_none: bool = True,
                    multi: Literal['raise',
                                   'first',
                                   'list',
                                   'warn_list',
                                   'warn_first',
                                   ] = 'warn_list',
                    verbose: bool = False,
                    deep_verbose: bool = False,
                    **kwargs
                    ) -> Product | int | Select | None:
        """Trouve un produit.

        Args:
            nomenclature: Nom de la nomenclature du produit recherché.
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            case_value: Recherche sensible à la casse.
            accent_value: Recherche sensible à l'accentuation.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `object`: L'objet `Product`.
                * `id`: L'identifiant de l'objet.
                * `query`: La requète de l'objet.
                * `queryid` ou `qid`: La requète de l'identifiant de l'object.
            raise_none: Si True, lève une [`SidbNotFoundError`][errors.SidbNotFoundError] si aucun
                élément ne correspond à la requète, renvoie `None` sinon.
            multi: Action à prendre quand plusieurs éléments correspondents à la requète
                Les valeurs possibles sont:

                 * `warn_list`: Affiche un avertissement et renvoie la liste des éléments.
                 * `warn_first`: Affiche un avertissement et renvoie le premier élément.
                 * `raise`: Lève une AssertionError.
                 * `list`: Renvoie la liste des éléments correspondants.
                 * `first`: Renvoie le premier élément correspondant.
            verbose: Si True, décrit le déroulement de la fonction dans le shell.
            deep_verbose: Si True, décrit le déroulement des fonctions appelées dans le shell.

        Returns:
            (Product): L'object trouvé (ou une liste si multi=list)
            (int): L'identifiant de l'objet trouvé (ou une liste si multi=list)
            (Select): La requète de l'objet ou de l'identifiant
            (None): Aucun object trouvé.

        Raises:
            errors.SidbNotFoundError: Aucun produit n'a pu être trouvé avec ces critères.
            ValueError: Si les critères de recherche sont mauvais.

        FutureDev :
            Implementer l'option "use_alias" (True par design)
        """
        return self.get_mtobject_tap(Product,
                                     *args,
                                     nomenclature=nomenclature,
                                     like_value=like_value,
                                     case_value=case_value,
                                     accent_value=accent_value,
                                     return_type=return_type,
                                     raise_none=raise_none,
                                     multi=multi,
                                     verbose=verbose,
                                     deep_verbose=deep_verbose,
                                     **kwargs)

    def get_products(self,
                     *args,
                     like_value: bool = False,
                     case_value: bool = True,
                     accent_value: bool = True,
                     map_id: Iterable[int] | int | Select = [],
                     return_type: Literal['list',
                                          'object',
                                          'id',
                                          'query',
                                          'queryid',
                                          'qid',
                                          'count',
                                          ] = 'list',
                     cache_properties: list[str] = [],
                     nomenclature: str | None = None,
                     verbose: bool = False,
                     deep_verbose: bool = False
                     ) -> list[Product] | list[int] | int | Select:
        """Trouve plusieurs produits.

        Args:
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            case_value: Recherche sensible à la casse.
            accent_value: Recherche sensible à l'accentuation.
            map_id: Filtre d'identifiants des objets.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets `Product`.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            nomenclature: Nom de la nomenclature des produits recherchés.
            verbose: Si True, est bavard.
            deep_verbose: Si True, est plus bavard.

        Returns:
            (list[Product]): Liste des produits recherchés.
            (list[int]): List des identifiants des produits recherchés.
            (int): Nombre de produits correspondants aux arguments donnés.
            (Select): Requète des produits ou des identifiants.

        Raises:
            ValueError: Paramètres invalides.
        """
        return self.get_mtobjects_tap(Product,
                                      *args,
                                      like_value=like_value,
                                      case_value=case_value,
                                      accent_value=accent_value,
                                      map_id=map_id,
                                      return_type=return_type,
                                      cache_properties=cache_properties,
                                      nomenclature=nomenclature,
                                      verbose=verbose,
                                      deep_verbose=deep_verbose)

    def get_products_by_ids(self,
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
                            ) -> list[Product] | int | Select:
        """Trouve les produits correspondants aux identifiants.

        Args:
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
            (list[Product]): Liste des produits correspondants.
            (int): Nombre d'objets contenus dans l'objet passé en paramètre.
            (Select): Requète des produit ou des identifiants.
        """
        return self.get_mtobjects_by_ids(Product, ids=ids,
                                         cache_properties=cache_properties,
                                         return_type=return_type,
                                         verbose=verbose)

    def get_products_in(self,
                        product: Product | list[Product],
                        self_include: bool = True,
                        cache_properties: list[str] = [],
                        return_type: Literal['list',
                                             'object',
                                             'id',
                                             'query',
                                             'queryid',
                                             'qid',
                                             'count',
                                             ] = "list",
                        verbose: bool = False
                        ) -> list[Product] | list[int] | int | Select:
        """Trouve des produits inclus dans le produit `product`.

        Args:
            product: L'object `Product` contenant des produits.
            self_include: Inclure ou non l'élément passé en paramètre.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            verbose: Si True, est bavard.

        Returns:
            (list[Product]): Liste des objets contenus dans l'objet passé en paramètre.
            (list[int]): List des identifiants des objets contenus dans l'objet passé en paramètre.
            (int): Nombre d'objets contenus dans l'objet passé en paramètre.
            (Select): Requète des objets.
        """
        return self.get_mtobjects_tap_in(product,
                                         Product,
                                         self_include=self_include,
                                         cache_properties=cache_properties,
                                         return_type=return_type,
                                         verbose=verbose)

    def get_products_on(self,
                        product: Product,
                        self_include: bool = True,
                        cache_properties: list[str] = [],
                        return_type: Literal['list',
                                             'object',
                                             'id',
                                             'query',
                                             'queryid',
                                             'qid',
                                             'count',
                                             ] = "list",
                        ) -> list[Product] | list[int] | int | Select:
        """Trouve les produits incluant le produit `product`.

        Args:
            product: L'object `Product` inclus dans d'autres produits.
            self_include: Inclure ou non l'élément passé en paramètre.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.

        Returns:
            (list[Product]): Liste des objets contenant l'objet passé en paramètre.
            (list[int]): List des identifiants des objets contenant l'objet passé en paramètre.
            (int): Nombre d'objets contenant l'objet passé en paramètre.
            (Select): Requète des objets ou des identifiants.
        """
        return self.get_mtobjects_tap_on(product, Product,
                                         self_include=self_include,
                                         cache_properties=cache_properties,
                                         return_type=return_type)

    def get_product_list(self,
                         nomenclature: str,
                         cache_properties: list[str] = [],
                         return_type: Literal['list',
                                              'object',
                                              'id',
                                              'query',
                                              'queryid',
                                              'qid',
                                              'count',
                                              ] = "list",
                         verbose: bool = False,
                         deep_verbose: bool = False
                         ) -> list[Product] | list[int] | int | Select:
        """Trouve des produits par nomenclature.

        Args:
            nomenclature: La nomenclature des produits à rechercher.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets `Product`.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            verbose: Si True, décrit le déroulement de la fonction dans le shell.
            deep_verbose: Si True, décrit le déroulement des fonctions appelées dans le shell.

        Returns:
            (list[Product]): Liste des produits recherchés.
            (list[int]): List des identifiants des produits recherchés.
            (int): Nombre de produits correspondants aux arguments donnés.
            (Select): Requète des produits ou des identifiants.
        """
        return self.get_mtobjects_tap(Product,
                                      "Nomenclature",
                                      nomenclature,
                                      cache_properties=cache_properties,
                                      nomenclature=nomenclature,
                                      verbose=verbose,
                                      deep_verbose=deep_verbose)

    def get_products_in_conversion(self,
                                   product: Product | Iterable[Product],
                                   dest_nomenclature,
                                   return_type: Literal['list',
                                                        'object',
                                                        'id',
                                                        'query',
                                                        'queryid',
                                                        'qid',
                                                        'count',
                                                        ] = "list",
                                   ):
        """
        Convertit un produit en ses produits dérivés dans une autre nomenclature, hiérarchie inclue.
        Si product est une liste de produits, ils doivent tous avoir la même nomenclature.

        FutureDev:
            Améliorer Prototype
        """
        if isinstance(product, Product):
            nomenclature = product.get_property('Nomenclature', multi='first')
        else:
            nomenclature = product[0].get_property('Nomenclature', multi='first')

        set_sel = set(self.get_products(f"ConversionProductCode@{dest_nomenclature}", "*",
                                        nomenclature=nomenclature,
                                        return_type="id"))
        set_sel &= set(self.get_products_in(product, return_type="id"))

        stmt = select(Property.value_literal)
        stmt = stmt.where(Property.item_id.in_(set_sel))
        stmt = stmt.where(Property.name_a == "ConversionProductCode")
        stmt = stmt.where(Property.name_b == f"{dest_nomenclature}").distinct()

        result = self.session.scalars(stmt).all()
        return [self.get_product(code=r[0], nomenclature=dest_nomenclature) for r in result]

    def get_list_nomenclatures(self) -> list[str]:
        """Renvoie la liste des nomenclatures."""
        stmt = select(Property.value_literal).filter_by(name_a='Nomenclature').distinct()
        return self.session.scalars(stmt).all()

    def get_root_nomenclature(self,
                              nomenclature: str,
                              verbose: bool = False
                              ) -> Product:
        """Trouve le produit original d'une nomenclature.

        Args:
            nomenclature: La nomenclature recherchée.
            verbose: Si True, décrit le déroulement de la fonction dans le shell.

        Returns:
            Le produit trouvé.

        Raises:
            SidbMultiFoundError: Plusieurs produits originaux trouvés.
        """
        p = self.get_products("Nomenclature", nomenclature)[0]
        if verbose:
            print(f"Found {p=}")
        lstp = self.get_products_on(p, cache_properties=["IsInProduct"])
        if verbose:
            print(f"Found {lstp=}")
        _returnp = None
        for _p in lstp:
            _isinprop = _p.get_property("IsInProduct", force_cache=True, raise_none=False)
            if verbose:
                print(f"Check {_isinprop=}")
            if _isinprop is None:
                if verbose:
                    print(">>> Is None !")
                if _returnp is not None:
                    raise SidbMultiFoundError(f"Multi root found in nomenclature {nomenclature}")
                _returnp = _p
        if verbose:
            print(f"returning {_returnp=}")
        return _returnp

    def load_product(self,
                     mapper: Mapper,
                     verbose: bool = False
                     ) -> None:
        """Charge un produit et ses propriétés dans la base de données.

        Args:
            mapper: Le mapper contenant les informations du produit.
            verbose:

        Raises:
            MapperError: Une erreur s'est produite.
        """
        product = None
        if mapper.primary_key != -1:
            iprimarykeys = [i for i, pk in enumerate(mapper.primarykeys) if pk]
            for ipk in iprimarykeys:
                mapper_ipk = mapper.get_dict_i(ipk)
                product = self.get_product(mapper_ipk["key"], mapper_ipk["value"],
                                           nomenclature=mapper.get("Nomenclature"),
                                           raise_none=False)
                if product is not None:
                    break
        else:
            lst_i_keys = mapper.get_keys_index("Code", startswith=True)
            lst_i_keys += mapper.get_keys_index("Name", startswith=True)
            for ikey in lst_i_keys:
                dict_key = mapper.get_dict_i(ikey)
                product = self.get_product(dict_key["key"], dict_key["value"],
                                           nomenclature=mapper.get("Nomenclature"),
                                           raise_none=False)
                if product is not None:
                    break

        if product is None:
            product = Product()
            self.session.add(product)
        product.delete_cached_properties()

        product.set_extra_properties(mapper)
        result = {}
        result["code"] = product.set_code(mapper)
        result["name"] = product.set_name(mapper)
        result["nomenclature"] = product.set_nomenclature(mapper)
        result["isinproduct"] = product.set_isin_product(mapper)

        # Recherche des erreurs
        if result["code"][0] != "OK" and result["name"][0] != "OK":
            raise MapperError(mapper, result, "name/code")
        elif result["code"][0] != "OK" and result["code"][0] != "NO_DATA":
            raise MapperError(mapper, result, "code")
        elif result["name"][0] != "OK" and result["name"][0] != "NO_DATA":
            raise MapperError(mapper, result, "name")
        if result["nomenclature"][0] != "OK":
            raise MapperError(mapper, result, "nomenclature")
        if result["isinproduct"][0] != "OK" and result["isinproduct"][0] != "NO_DATA":
            raise MapperError(mapper, result, "isinproduct")
