from __future__ import annotations

import typing
from typing import Literal, Iterable

from sinamet.mtobjects.gateflow import Gateflow
from sinamet.core.mapper import MapperError

if typing.TYPE_CHECKING:
    from datetime import date
    from sqlalchemy import Select
    from sinamet.mtobjects.territory import Territory
    from sinamet.mtobjects.actor import Actor
    from sinamet.mtobjects.product import Product
    from sinamet.core.mapper import Mapper


class SidbGateflow:
    def get_gateflows(self,
                      target: list[Territory | Actor] = [],
                      flowtype: Literal['input', 'output',
                                        'comsumption',
                                        'production',
                                        'extraction',
                                        'emission', None] = None,
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
                      ) -> list[Gateflow] | list[int] | int | Select:
        """Trouve des flux de porte (Gateflow).

        Parameters:
            target: Le territoire et/ou l'acteur lié(s) aux flux.
            flowtype: Type de flux, peut être `input`, `output`, `comsumption`,
                `production`, `extraction` ou `emission`.
            product: Le produit lié aux flux.
            product_asc: Effectue une recherche ascendante sur le produit,
                recherche le produit et ses parents.
            product_desc: Effectue une recherche descendante sur le produit,
                recherche le produit et ses enfants.
            date_point: La date ponctuelle des flux.
            date_start: La date de départ des flux.
            date_end: La date de fin des flux.
            year: L'année des flux.
            month: Le mois des flux.
            sourceref: La source de référence des flux.
            filter_by: Liste de propriétés supplémentaires pour le filtrage des
                flux (ex. [("Label", "Bio")]).
            use_or: Si `True`, compare les `target` en utilisant un ou binaire,
                sinon compare en utilisant un et binaire.
            map_id: Filtre d'identifiants des objets.
            cache_properties: Liste des propriétés à mettre en cache.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des flux `Gateflow`.
                * `id`: La liste des identifiants des flux.
                * `query`: La requète des flux.
                * `queryid` ou `qid`: La requète des identifiants des flux.
                * `count`: Nombre de flux correspondants.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.

        Returns:
            (list[Gateflow]): Liste des flux recherchés.
            (list[int]): Liste des identifiants des flux recherchés.
            (int): Nombre de flux correspondants aux arguments donnés.
            (Select): Requète des flux ou des identifiants.

        Note: FutureDev
            - Implementer target_(asc/desc).
        """
        return self.get_mtobjects_gs(Gateflow, target=target, flowtype=flowtype,
                                     product=product, product_asc=product_asc,
                                     product_desc=product_desc, date_point=date_point,
                                     date_start=date_start, date_end=date_end,
                                     year=year, month=month, sourceref=sourceref,
                                     filter_by=filter_by, use_or=use_or,
                                     map_id=map_id,
                                     cache_properties=cache_properties,
                                     return_type=return_type, verbose=verbose)

    def get_inputs(self,
                   target: list[Territory | Actor] = [],
                   **kwargs
                   ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux d'entrée de `target`.

        Fonction wrapper de [get_gateflows][sidb.gateflow.SidbGateflow.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="input", **kwargs)

    def get_outputs(self,
                    target: list[Territory | Actor] = [],
                    **kwargs
                    ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux de sortie de `target`.

        Fonction wrapper de [get_gateflows][sidb.gateflow.SidbGateflow.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="output", **kwargs)

    def get_consumptions(self,
                         target: list[Territory | Actor] = [],
                         **kwargs
                         ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux de consommation de `target`.

        Fonction wrapper de [get_gateflows][sidb.gateflow.SidbGateflow.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="consumption", **kwargs)

    def get_productions(self,
                        target: list[Territory | Actor] = [],
                        **kwargs
                        ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux de production de `target`.

        Fonction wrapper de [get_gateflows][sidb.gateflow.SidbGateflow.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="production", **kwargs)

    def get_extractions(self,
                        target: list[Territory | Actor] = [],
                        **kwargs
                        ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux d'extraction de `target`.

        Fonction wrapper de [get_gateflows][sidb.gateflow.SidbGateflow.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="extraction", **kwargs)

    def get_emissions(self,
                      target: list[Territory | Actor] = [],
                      **kwargs
                      ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux d'émission de `target`.

        Fonction wrapper de [get_gateflows][sidb.gateflow.SidbGateflow.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="emission", **kwargs)

    def load_gateflow(self,
                      mapper: Mapper,
                      flowtype: Literal['input', 'output',
                                        'comsumption',
                                        'production'
                                        'extraction'
                                        'emission', None] = None,
                      verbose: bool = False
                      ) -> None:
        """Charge un flux de porte et ses propriétés dans la base de données.

        Args:
            mapper: Le mapper contenant les informations du flux.
            flowtype: Le type de flux.
            verbose:
        """
        if flowtype is not None:
            mapper.add("FlowType", flowtype, sourceref=mapper.all_srcref)

        obj = Gateflow()
        self.session.add(obj)
        # Créer un attribut (objet) par champ du dictionnaire
        # Ajout des attributs non fonctionnels
        obj.set_extra_properties(mapper)
        result = {}
        result["flowtype"] = obj.set_flowtype(mapper)
        result["product"] = obj.set_product(mapper)
        result["quantity"] = obj.set_quantity(mapper)
        result["timeperiod"] = obj.set_timeperiod(mapper)
        result["territory"] = obj.set_territory(mapper)
        result["actor"] = obj.set_actor(mapper)

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
