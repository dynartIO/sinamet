from typing import TypeVar
from typing import Literal
from typing import Iterable

from datetime import date

from sqlalchemy.sql import or_, and_, select, Select
from sqlalchemy.orm import aliased

from sinamet.mtobjects.pathflow import Pathflow
from sinamet.mtobjects.territory import Territory
from sinamet.mtobjects.actor import Actor
from sinamet.mtobjects.product import Product
from sinamet.mtobjects.property import Property
from sinamet.tools.timext import get_start_end_dates, to_date
from sinamet.core.mapper import Mapper, MapperError

T = TypeVar('T', Territory, Actor)


class SidbPathflow:
    def get_pathflows(self,
                      target: T | None = None,
                      direction: Literal['import', 'export',
                                         'internal', 'all',
                                         None] = None,
                      btarget: T | None = None,
                      xtarget: T | None = None,
                      product: Product | None = None,
                      product_asc: bool = False,
                      product_desc: bool = True,
                      date_point: date | str | None = None,
                      date_start: date | str | None = None,
                      date_end: date | str | None = None,
                      year: str | int | None = None,
                      month: str | int | None = None,
                      sourceref: str | None = None,
                      filter_by: list[tuple[str, str]] = [],
                      map_id: Iterable[int] | int | Select = [],
                      return_type: Literal['list', 'object',
                                           'id', 'query',
                                           'queryid', 'qid',
                                           'count'] = 'list',
                      cache_properties: list[str] = [],
                      ) -> list[Pathflow] | list[int] | int | Select:
        """Trouve des flux de chemin (Pathflow).

        Parameters:
            target: Le territoire et/ou l'acteur lié(s) aux flux.
            direction: La direction des flux, peut être `import`, `export`,
                `internal` ou `all`.
            btarget: Cible complémentaire.
            xtarget: Cible exclue.
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
            map_id: Filtre d'identifiants des objets.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des flux `Pathflow`.
                * `id`: La liste des identifiants des flux.
                * `query`: La requète des flux.
                * `queryid` ou `qid`: La requète des identifiants des flux.
                * `count`: Nombre de flux correspondants.
            cache_properties: Liste des propriétés à mettre en cache.

        Returns:
            (list[Pathflow]): Liste des flux recherchés.
            (list[int]): Liste des identifiants des flux recherchés.
            (int): Nombre de flux correspondants aux arguments donnés.
            (Select): Requète des flux ou des identifiants.

        Note: FutureDev
            - Implementer target_(asc/desc).
        """
        if direction not in ["import", "export", "internal", "all"] and direction is not None:
            raise ValueError(f"Unknown direction = '{direction}'")
        if type(target) is list:
            raise ValueError("Target list is not configured yet")
        if (xtarget is not None) or (btarget is not None):
            if (direction == "internal") or (direction == "all"):
                raise ValueError(f"xtarget or btarget should be None for '{direction}' direction flow")
        if product is None:
            print("WARNING: Product = None is not advised")

        date_point = to_date(date_point)
        date_start, date_end = get_start_end_dates(start=date_start, end=date_end,
                                                   year=year, month=month)

        q = {}
        for nq, targetq in zip(["id", "object"], [Pathflow.id, Pathflow]):
            q[nq] = select(targetq)
            if sourceref is not None:
                q[nq] = q[nq].join(Pathflow.properties).where(Property.sourceref == sourceref)
            if date_point:
                q[nq] = q[nq].where(or_(Pathflow.date_point == date_point,
                                        and_(Pathflow.date_start <= date_point,
                                             Pathflow.date_end >= date_point)))
            elif date_start != date.min or date_end != date.max:
                q[nq] = q[nq].where(or_(and_(Pathflow.date_start <= date_end,
                                             Pathflow.date_end >= date_start),
                                        and_(Pathflow.date_point <= date_end,
                                             Pathflow.date_point >= date_start)))
            if product is not None:
                products_search = []
                if product_desc:
                    products_search.append(Pathflow.product_id.in_(
                        self.get_products_in(product, return_type="qid")
                        ))
                if product_asc:
                    products_search.append(Pathflow.product_id.in_(
                        self.get_products_on(product, return_type="qid")
                        ))
                if not products_search:
                    products_search.append(Pathflow.product_id == product.id)
                q[nq] = q[nq].where(or_(*products_search))

            if type(target) is Territory:
                # ToDo : Implement Actors continuation
                # Vérify xtarget type
                if xtarget is not None and type(xtarget) is not Territory:
                    raise TypeError(f"xtarget '{xtarget}' is not a Territory")
                if btarget is not None and type(btarget) is not Territory:
                    raise TypeError(f"btarget '{btarget}' is not a Territory")
                if direction == "import":
                    q[nq] = q[nq].where(and_(~Pathflow.emitter_territory_id.in_(self.get_territories_in(target, return_type="qid")),
                                             Pathflow.receiver_territory_id.in_(self.get_territories_in(target, return_type="qid"))))
                    if xtarget is not None:
                        q[nq] = q[nq].where(~Pathflow.emitter_territory_id.in_(self.get_territories_in(xtarget, return_type="qid")))
                    if btarget is not None:
                        q[nq] = q[nq].where(Pathflow.emitter_territory_id.in_(self.get_territories_in(btarget, return_type="qid")))
                elif direction == "internal":
                    q[nq] = q[nq].where(and_(or_(Pathflow.emitter_territory_id.in_(self.get_territories_in(target, return_type="qid")),
                                                 Pathflow.emitter_actor_id.in_(self.get_actors_in(target, return_type="qid"))),
                                             or_(Pathflow.receiver_territory_id.in_(self.get_territories_in(target, return_type="qid")),
                                                 Pathflow.receiver_actor_id.in_(self.get_actors_in(target, return_type="qid")))))
                elif direction == "export":
                    q[nq] = q[nq].where(and_(Pathflow.emitter_territory_id.in_(self.get_territories_in(target, return_type="qid")),
                                             ~Pathflow.receiver_territory_id.in_(self.get_territories_in(target, return_type="qid"))))
                    if xtarget is not None:
                        q[nq] = q[nq].where(~Pathflow.receiver_territory_id.in_(self.get_territories_in(xtarget, return_type="qid")))
                    if btarget is not None:
                        q[nq] = q[nq].where(Pathflow.receiver_territory_id.in_(self.get_territories_in(btarget, return_type="qid")))
                elif direction == "all":
                    q[nq] = q[nq].where(or_(Pathflow.emitter_territory_id.in_(self.get_territories_in(target, return_type="qid")),
                                            Pathflow.receiver_territory_id.in_(self.get_territories_in(target, return_type="qid"))))
                # x- and b-target
            elif type(target) is Actor:
                # ToDo : Implement Actors continuation
                # Vérify xtarget type
                if xtarget is not None and type(xtarget) is not Actor:
                    raise TypeError("xtarget '%s' is not an Actor" % xtarget)
                if btarget is not None and type(btarget) is not Actor:
                    raise TypeError("btarget '%s' is not an Actor" % btarget)
                if direction == "import":
                    q[nq] = q[nq].where(and_(~Pathflow.emitter_actor_id.in_(self.get_actors_in(target, return_type="qid")),
                                             Pathflow.receiver_actor_id.in_(self.get_actors_in(target, return_type="qid"))))
                    if xtarget is not None:
                        q[nq] = q[nq].where(~Pathflow.emitter_actor_id.in_(self.get_actors_in(xtarget, return_type="qid")))
                    if btarget is not None:
                        q[nq] = q[nq].where(Pathflow.emitter_actor_id.in_(self.get_actors_in(btarget, return_type="qid")))
                elif direction == "internal":
                    q[nq] = q[nq].where(and_(Pathflow.emitter_actor_id.in_(self.get_actors_in(target, return_type="qid")),
                                             Pathflow.receiver_actor_id.in_(self.get_actors_in(target, return_type="qid"))))
                elif direction == "export":
                    q[nq] = q[nq].where(and_(Pathflow.emitter_actor_id.in_(self.get_actors_in(target, return_type="qid")),
                                             ~Pathflow.receiver_actor_id.in_(self.get_actors_in(target, return_type="qid"))))
                    if xtarget is not None:
                        q[nq] = q[nq].where(~Pathflow.receiver_actor_id.in_(self.get_actors_in(xtarget, return_type="qid")))
                    if btarget is not None:
                        q[nq] = q[nq].where(Pathflow.receiver_actor_id.in_(self.get_actors_in(btarget, return_type="qid")))
                elif direction == "all":
                    q[nq] = q[nq].where(or_(Pathflow.emitter_actor_id.in_(self.get_actors_in(target, return_type="qid")),
                                            Pathflow.receiver_actor_id.in_(self.get_actors_in(target, return_type="qid"))))
                # x- and b-target
            elif target is not None:
                raise AttributeError("Unknwon target type = %s (%s)" % (type(target), target))

            for name, value in filter_by:
                p = aliased(Property)
                name_a, *name_b = name.split('@', 1)
                q[nq] = (q[nq].join(p, Pathflow.properties)
                         .where(p.name_a == name_a))
                if name_b:
                    q[nq] = q[nq].where(p.name_b == name_b[0])
                if value != '*':
                    q[nq] = q[nq].where(p.value_literal == value)

            if map_id:
                if (isinstance(map_id, int)):
                    map_id = (map_id,)
                q[nq] = q[nq].where(Pathflow.id.in_(map_id))

        returnval = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return returnval

    def get_imports(self,
                    target: T | None = None,
                    **kwargs
                    ) -> list[Pathflow] | list[int] | int | Select:
        """
        Retourne les flux importés: ceux dont l'origine est à l'extérieur de
        `target` et la destination est à l'intérieur.

        Fonction wrapper de [get_pathflows][sidb.pathflow.SidbPathflow.get_pathflows].
        """
        return self.get_pathflows(target, direction="import", **kwargs)

    def get_exports(self,
                    target: T | None = None,
                    **kwargs
                    ) -> list[Pathflow] | list[int] | int | Select:
        """
        Retourne les flux exportés: ceux dont l'origine est à l'intérieur de
        `target` et la destination est à l'extérieur.

        Fonction wrapper de [get_pathflows][sidb.pathflow.SidbPathflow.get_pathflows].
        """
        return self.get_pathflows(target, direction="export", **kwargs)

    def get_internals(self,
                      target: T | None = None,
                      **kwargs
                      ) -> list[Pathflow] | list[int] | int | Select:
        """
        Retourne les flux internes: ceux dont l'origine et la destination sont
        dans `target`.

        Fonction wrapper de [get_pathflows][sidb.pathflow.SidbPathflow.get_pathflows].
        """
        return self.get_pathflows(target, direction="internal", **kwargs)

    def load_pathflow(self, mapper: Mapper, verbose: bool = False) -> None:
        """Charge un flux de chemin et ses propriétés dans la base de données.

        Args:
            mapper: Le mapper contenant les informations du flux.
            verbose:
        """
        pathflow = Pathflow()
        self.session.add(pathflow)

        pathflow.set_extra_properties(mapper)
        result = {}
        result["quantity"] = pathflow.set_quantity(mapper)
        result["timeperiod"] = pathflow.set_timeperiod(mapper)
        result["product"] = pathflow.set_product(mapper)
        result["emitter_territory"] = pathflow.set_emitter_territory(mapper)
        result["emitter_actor"] = pathflow.set_emitter_actor(mapper)
        result["receiver_territory"] = pathflow.set_receiver_territory(mapper)
        result["receiver_actor"] = pathflow.set_receiver_actor(mapper)

        # Recherche des erreurs
        if result["receiver_territory"][0] != "OK" and result["receiver_actor"][0] != "OK":
            raise MapperError(mapper, result, "receiver_territory/receiver_actor")
        if result["emitter_territory"][0] != "OK" and result["emitter_actor"][0] != "OK":
            raise MapperError(mapper, result, "emitter_territory/emitter_actor")
        if result["quantity"][0] != "OK":
            raise MapperError(mapper, result, "quantity")
        if result["timeperiod"][0] != "OK":
            raise MapperError(mapper, result, "timeperiod")
        if result["product"][0] != "OK":
            raise MapperError(mapper, result, "product")
