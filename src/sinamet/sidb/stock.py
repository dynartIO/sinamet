from typing import Literal, Iterable

from datetime import date

from sqlalchemy import Select

from sinamet.mtobjects.stock import Stock
from sinamet.mtobjects.territory import Territory
from sinamet.mtobjects.actor import Actor
from sinamet.mtobjects.product import Product
from sinamet.core.mapper import Mapper, MapperError


class SidbStock:
    def get_stocks(self,
                   target: list[Territory | Actor] = [],
                   product: Product | None = None,
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
                   return_type: Literal['list', 'object',
                                        'id', 'query',
                                        'queryid', 'qid',
                                        'count'] = 'list',
                   cache_properties: list[str] = [],
                   verbose: bool = False
                   ) -> list[Stock] | list[int] | int | Select:
        """Trouve des stocks (Stock).

        Parameters:
            target: Le territoire et/ou l'acteur lié(s) aux stocks.
            product: Le produit lié aux stocks.
            product_asc: Effectue une recherche ascendante sur le produit,
                recherche le produit et ses parents.
            product_desc: Effectue une recherche descendante sur le produit,
                recherche le produit et ses enfants.
            date_point: La date ponctuelle des stocks.
            date_start: La date de départ des stocks.
            date_end: La date de fin des stocks.
            year: L'année des stocks.
            month: Le mois des stocks.
            sourceref: La source de référence des stocks.
            filter_by: Liste de propriétés supplémentaires pour le filtrage des
                stocks (ex. [("Label", "Bio")]).
            use_or: Si `True`, compare les `target` en utilisant un ou binaire,
                sinon compare en utilisant un et binaire.
            map_id: Filtre d'identifiants des objets.
            cache_properties: Liste des propriétés à mettre en cache.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des stocks `Stock`.
                * `id`: La liste des identifiants des stocks.
                * `query`: La requète des stocks.
                * `queryid` ou `qid`: La requète des identifiants des stocks.
                * `count`: Nombre de stocks correspondants.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.

        Returns:
            (list[Stock]): Liste des stocks recherchés.
            (list[int]): Liste des identifiants des stocks recherchés.
            (int): Nombre de stocks correspondants aux arguments donnés.
            (Select): Requète des stocks ou des identifiants.

        Note: FutureDev
            - Implementer target_(asc/desc).
        """
        return self.get_mtobjects_gs(Stock, target=target, product=product,
                                     product_asc=product_asc,
                                     product_desc=product_desc, date_point=date_point,
                                     date_start=date_start, date_end=date_end,
                                     year=year, month=month, sourceref=sourceref,
                                     filter_by=filter_by, use_or=use_or,
                                     map_id=map_id,
                                     cache_properties=cache_properties,
                                     return_type=return_type, verbose=verbose)

    def load_stock(self,
                   mapper: Mapper,
                   verbose: bool = False
                   ) -> None:
        """Charge un stock et ses propriétés dans la base de données.

        Args:
            mapper: Le mapper contenant les informations du stock.
            verbose:
        """
        stock = Stock()
        self.session.add(stock)
        # Créer un attribut (objet) par champ du dictionnaire
        # Ajout des attributs non fonctionnels
        stock.set_extra_properties(mapper)
        result = {}
        result["code"] = stock.set_code(mapper)
        result["product"] = stock.set_product(mapper)
        result["quantity"] = stock.set_quantity(mapper)
        result["timeperiod"] = stock.set_timeperiod(mapper)
        result["territory"] = stock.set_territory(mapper)
        result["actor"] = stock.set_actor(mapper)

        if result["code"][0] == "WRONG_DATA_TYPE":
            raise MapperError(mapper, result, "code")
        if result["quantity"][0] != "OK":
            raise MapperError(mapper, result, "quantity")
        if result["timeperiod"][0] != "OK":
            raise MapperError(mapper, result, "timeperiod")
        if result["product"][0] != "OK":
            raise MapperError(mapper, result, "product")
        if result["territory"][0] != "OK" and result["territory"][0] != "NO_DATA":
            raise MapperError(mapper, result, "territory")
        if result["actor"][0] != "OK" and result["actor"][0] != "NO_DATA":
            raise MapperError(mapper, result, "actor")
