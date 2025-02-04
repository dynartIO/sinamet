from __future__ import annotations

from collections.abc import Iterable, Iterator

from contextlib import contextmanager

from datetime import date

from typing import Any, Literal, Sequence, TypeVar

import warnings

from sqlalchemy import ColumnElement, Engine, create_engine
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.orm.session import Session, object_session, sessionmaker
from sqlalchemy.sql import Select, and_, delete, func, or_, select

from sinamet.config import config
from sinamet.mapper import Mapper, MapperError
from sinamet.errors import SidbMultiFoundError, SidbNotFoundError
from sinamet.mtobjects.actor import Actor
from sinamet.mtobjects.dbobject import DBObjectClassBase
from sinamet.mtobjects.gateflow import Gateflow
from sinamet.mtobjects.mtobject import MTObject
from sinamet.mtobjects.pathflow import Pathflow
from sinamet.mtobjects.product import Product
from sinamet.mtobjects.property import Property
from sinamet.mtobjects.stock import Stock
from sinamet.mtobjects.territory import Territory
from sinamet.tools.timext import get_start_end_dates, to_date


class Sidb:
    sessionmakers: dict[str, sessionmaker[Session]] = {}
    sessions: list[Sidb] = []

    def __init__(self, session: Session):
        self.session: Session = session
        self.cache: dict[tuple[str, str, str], MTObject] = {}

    @contextmanager
    @staticmethod
    def connect(autocommit: bool = True,
                verbose: bool = False,
                **kwargs: str
                ) -> Iterator[Sidb]:
        """Gestionnaire de contexte permettant une connexion à la base de donnée.

        Parameters:
            autocommit: Commit les transactions en attente automatiquement en
                quittant le contexte.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.
            kwargs: Informations de connexion à la base de donnée.
        """
        Session = Sidb.sessionmakers.get(config.current_environref)
        if not Session:
            if verbose:
                print(f"No sessionmaker found for {config.current_environref=}.")
            if not (db_path := config.get('COREDB_PATH')):
                db_path = config.init_db(verbose=verbose, **kwargs)
            engine = create_engine(db_path)
            DBObjectClassBase.metadata.create_all(engine)
            Session = sessionmaker(engine)
            Sidb.sessionmakers[config.current_environref] = Session
        elif verbose:
            print(f"Found a sessionmaker for {config.current_environref=}.")
        session = Session()
        sidb = Sidb(session)
        Sidb.sessions.append(sidb)
        try:
            yield sidb
            if autocommit:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if verbose:
                print("Closing session.")
            session.close()
            Sidb.sessions.remove(sidb)

    @staticmethod
    def get_sidb_from_object(obj: MTObject) -> Sidb:
        """Récupère la session de connexion liée à un objet.

        Parameters:
            obj: L'objet dont on veut récupérer la session.

        Returns:
            L'instance de connexion liée à l'objet.

        Raises:
            ValueError: L'objet n'est pas associé à une session connue.
        """
        try:
            obj_session = object_session(obj)
            for sidb in Sidb.sessions:
                if sidb.session == obj_session:
                    return sidb
        except UnmappedInstanceError:
            pass
        raise ValueError(f'No session found for the object \'{obj}\'.')

    def load(self, mapper: Mapper, raise_error: bool = True,
             verbose: bool = False) -> None:
        """Charge un Mapper vers dans la base de donnée (créé ou met à jour le MTObject
        correspondant).

        Parameters:
            mapper: L'objet `Mapper` contenant les informations de l'objet à charger.
            raise_error: Si `True`, lève une erreur si l'objet n'a pas été chargé
                correctement.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.

        Raises:
            MapperError: Les informations du mapper sont incorrectes.
            ValueError: Le type du mapper est inconnu.
        """
        if verbose:
            print(mapper)

        try:
            if mapper.type in ["input", "output", "consumption", "production",
                               "extraction", "emission", "internal"]:
                return self.load_gateflow(mapper, flowtype=mapper.type, verbose=verbose)

            # Call load function of mapper.type object.
            f = getattr(self, f"load_{mapper.type}", None)
            if f is None:
                raise ValueError(f"Unknown mapper type: '{mapper.type}'")
            return f(mapper, verbose=verbose)
        except MapperError as error:
            if raise_error:
                raise
            print(f"MapperError: {error}")
        except Exception:
            print(f"{mapper}")
            raise

    def delete(self, obj: MTObject | Property, verbose: bool = False) -> None:
        """Supprime un objet de la base de donnée.

        Parameters:
            obj: L'objet à suprimer.
            verbose: Si `True`, décrit le déroulement de la fonction dans le shell.
        """
        if verbose:
            print(f"Delete '{obj}' (type={type(obj)})")

        self.session.delete(obj)

    def delete_source_ref(self,
                          source_ref: str,
                          exclude: str | Iterable[str] = [],
                          recursive: bool = False) -> None:
        """Supprime une source de référence.

        Supprime une source de référence en supprimant les propriétés qui lui sont liées.

        Parameters:
            source_ref: La source de référence à supprimer.
            exclude: Liste de noms de propriétés à ne pas supprimer.
            recursive: Si `True`, supprime également les sources enfants de `source_ref`.
        """
        if isinstance(exclude, str):
            exclude = (exclude,)

        delete_stmt = delete(Property).where(Property.name_a.not_in(exclude))
        if recursive:
            delete_stmt = delete_stmt.where(
                    (Property.source_ref.startswith(f'{source_ref}:'))
                    | (Property.source_ref == source_ref)
            )
        else:
            delete_stmt = delete_stmt.where(
                    Property.source_ref == source_ref
            )
        self.session.execute(delete_stmt)

        # Delete MTObjects without any properties left.
        self.session.execute(
                delete(MTObject)
                .where(~MTObject.properties.any())
        )

    def get_source_refs(self, subinclude: bool = True) -> list[str]:
        """Renvoie toutes les sources des propriétés enregistrées.

        Parameters:
            subinclude: Inclut la décomposition des noms des sources selon ":"
                ex: source:nom1:nom2 => [source, source:nom1, source:nom1:nom2]

        Returns:
            La liste des sources des propriétés.
        """
        src_lst = self.session.scalars(
                select(Property.source_ref).distinct()
                ).all()
        src_lst = set(filter(None, src_lst))
        if not subinclude:
            return sorted(src_lst)
        temp_add: list[str] = []
        for src in src_lst:
            temp = src.split(":")
            temp_compo = ""
            for substr in temp:
                temp_compo += substr
                if temp_compo not in src_lst and temp_compo not in temp_add:
                    temp_add.append(temp_compo)
                temp_compo += ":"
        src_lst.update(temp_add)
        return sorted(src_lst)

    def get_statistics(self) -> dict[str, list[str] | int]:
        """Obtiens les statistiques de la base de donnée.

        Returns:
            Un dictionnaire contenant:

                - Le nombre d'objet de chaque type (Territory, Actor, ...).
                - La liste des nomenclatures de produit.
                - La liste des echelles de territoire, et la quantité de territoire
                    leur appartenant.
                - La liste des sources de références.
                - La liste des noms de propriétés.
        """
        stats: dict[str, list[str] | int] = {}
        lstobjecttype = [Territory, Product, Actor, Stock, Gateflow, Pathflow, Property]
        for obj in lstobjecttype:
            stats[f"nb-mtobject-{obj.__tablename__}"] = self.session.scalar(
                                                            select(func.count(obj.id))
                                                        ) or 0
        stats["nomenclatures"] = self.get_list_nomenclatures()
        stats["scales"] = self.get_territory_scales()

        for sc in stats["scales"]:
            stmt = (select(func.count(Territory.id))
                    .join(Territory.properties)
                    .where((Property.name_a == 'Scale')
                           & (Property.value_literal == sc)))
            stats["nb-scale-" + sc.lower()] = self.session.scalar(stmt) or 0

        stats["source_refs"] = self.get_source_refs(False)
        stats["property_name"] = [f"{a}{'' if b is None else f'@{b}'}"
                                  for a, b in self.session.execute(
                                      select(Property.name_a, Property.name_b)
                                      .distinct()
                                      ).all()
                                  ]
        return stats

    def get_properties(self, properties: Iterable[str] | str,
                       map_id: Select | list[int] | None = None,
                       startlike: bool = False,
                       return_type: str = 'list') -> Sequence[Property]:
        """Charge et renvoie les propriétés correspondantes.

        Parameters:
            properties: Les noms des propriétés à charger.
            map_id: Si renseigné, charge uniquement les propriétés liées aux objets
                dont l'id correspond.
            startlike: Pas implémenté.
            return_type: Pas implémenté.

        Returns:
            La liste des propriétés correspondantes.
        """
        if startlike:
            raise ValueError('Not implemented yet.')

        if isinstance(properties, str):
            properties = (properties,)
        q = select(Property)
        mysqllst: list[ColumnElement[bool]] = []
        for prop in properties:
            mytabname = Property.tabname(prop)
            if mytabname[1] is not None:
                mysqllst.append(and_(Property.name_a == mytabname[0],
                                     Property.name_b == mytabname[1]))
            else:
                mysqllst.append(Property.name_a == mytabname[0])
        q = q.where(or_(*mysqllst))

        if map_id is not None:
            result = self.session.scalars(q.where(Property.item_id.in_(map_id)))
        else:
            result = self.session.scalars(q)
        return result.all()

    def get_property_with_id(self, id: int) -> Property | None:
        """Renvoie la propriété correspondant à l'identifiant.

        Parameters:
            id: L'identifiant de la propriété à renvoyer.

        Returns:
            La propriété correspondante ou `None` sinon.
        """
        return self.session.get(Property, id)

    def compute_query_return_type(self,
                                  qnq: dict[str, Select],
                                  return_type: Literal['qid', 'queryid',
                                                       'query', 'id',
                                                       'list', 'object',
                                                       'count']
                                  ) -> Select | Sequence[Any] | int:
        match return_type:
            case 'qid' | 'queryid':
                return qnq['id']
            case 'query':
                return qnq['object']
            case 'id':
                return self.session.scalars(qnq['id']).unique().all()
            case 'list' | 'object':
                return self.session.scalars(qnq['object']).unique().all()
            case 'count':
                return self.session.scalar(
                        select(func.count())
                        .select_from(qnq['id'].distinct().subquery())
                ) or 0
            case _:
                raise ValueError(f'Unknown return type, got {return_type}')

    def compute_query_cache_properties(self,
                                       cache_properties: list[str] | str,
                                       return_type: str,
                                       q_id: Select) -> None:
        """Charge en cache des propriétés.

        Parameters:
            cache_properties: La liste de propriétés à mettre en cache.
            return_type: Le type de retour.
            q_id: La requète des identifiants des objets dont on veut les
                propriétés.
        """
        if return_type not in ["list", "object"]:
            return

        s = {"Name", "Code"}
        if isinstance(cache_properties, str):
            s.add(cache_properties)
        else:
            s.update(cache_properties)
        self.get_properties(list(s), map_id=q_id)

    def get_distinct_property_values(self, prop_name: str) -> Sequence[str | None]:
        """
        Renvoie toutes les valeurs distinctes de propriétés avec
        un certain nom.

        Parameters:
            prop_name: Le nom de la propriétés dont on souhaite récupérer les
                valeurs. (Attention: ne peut pas avoir de précision)

        Returns:
            La liste des valeurs distinctes.
        """
        result = self.session.scalars(
                select(Property.value_literal)
                .where(Property.name_a == prop_name)
                .distinct()
        )
        return result.all()

    def is_loaded(self, source_ref: str) -> bool:
        """Détermine si une source est chargée.

        Parameters:
            source_ref: Le nom de la source à vérifier.

        Returns:
            `True` si la source est déjà chargée dans la base de donnée,
                `False` sinon.
        """
        return source_ref in self.get_source_refs(False)

    def is_not_loaded(self, source_ref: str) -> bool:
        """Détermine si une source n'est pas chargée.

        Parameters:
            source_ref: Le nom de la source à vérifier.

        Returns:
            `True` si la source n'est pas chargée dans la base de donnée,
                `False` sinon.
        """
        return source_ref not in self.get_source_refs(False)

    def progress(self, steps_commit: int = 1000,
                 steps_print: int = 20, commit: bool = True) -> None:
        """
        Cette fonction permet de suivre l'importation de données, en affichant
        la progression dans le shell (affichage de `+`),
        et en commitant régulièrement les transactions (tous les `steps_commit`
        appel).
        La fonction permet d'éviter de saturer la mémoire sur de grand imports.

        Parameters:
            steps_commit: Le nombre d'appel entre chaque commit.
            steps_print: Le nombre d'appel entre chaque affichage dans le shell.
            commit: Activer la fonction de commit (défault True)
        """
        if not hasattr(self, "progress_counter"):
            self.progress_counter = 0
        self.progress_counter += 1

        if not self.progress_counter % steps_print:
            print("+", end="", flush=True)

        if commit and not self.progress_counter % steps_commit:
            print(f"[{self.progress_counter}]")
            self.session.commit()

    def drop_all(self) -> None:
        """Ferme la session et supprime les tables de la base de donnée."""
        self.session.close()
        bind = self.session.bind
        if not bind:
            return
        DBObjectClassBase.metadata.drop_all(bind)
        if isinstance(bind, Engine):
            bind.dispose()

    def reset(self) -> None:
        """
        Ferme la session, supprime les tables de la base de donnée puis les
        recrée.
        """
        self.drop_all()
        if self.session.bind:
            DBObjectClassBase.metadata.create_all(self.session.bind)

    def get_cache(self, obj_type: str, key: str, value: str) -> MTObject | None:
        """Récupère l'objet en cache associé aux paramètres.

        Parameters:
            obj_type: Type de l'objet (Actor, Territory, ...).
            key: La clé de recherche (Name, Code).
            value: La valeur de la clé.

        Returns:
            L'objet correspondant ou `None` sinon.
        """
        return self.cache.get((obj_type, key, value))

    def set_cache(self, obj: MTObject, key: str, value: str) -> None:
        """Stock un objet dans le cache.

        Parameters:
            obj: L'objet à stocker dans le cache.
            key: La clé de recherche (Name, Code).
            value: La valeur de la clé.
        """
        self.cache[(obj.__class__.__name__, key, value)] = obj

    def clear_cache(self) -> None:
        """Vide le cache d'objet."""
        self.cache = {}

    # Territory
    def get_territory(self,
                      *args,
                      like_value: bool = False,
                      ignore_case: bool = False,
                      ignore_accent: bool = False,
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
                      **kwargs
                      ) -> Territory | int | Select | None:
        """Trouve un territoire.

        Examples:
            >>> territory = get_territory(code="16")
            >>> territory = get_territory("Name", "Saint-%", like_value=True)

        Args:
            *args: Duo d'arguments "NomDeProprieté", "Valeur", ou chaîne-objet "Territory(Code=xxxxx)", ou vide si kwargs renseignés
            **kwargs: code=="xxxxx" ou code_insee="xxxxx" ou name="xxxxxx" ou name_fr="xxxxx"
            like_value: Si True, la valeur est recherchée à travers
                l'[instruction LIKE de SQL](https://www.postgresql.org/docs/current/functions-matching.html#FUNCTIONS-LIKE)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            ignore_case: Recherche ignorant la casse.
            ignore_accent: Recherche ignorant l'accentuation.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `object`: L'objet `Territory`.
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
            verbose: Si True, est bavard.

        Returns:
            (Territory): L'object trouvé.
            (int): L'identifiant de l'objet trouvé.
            (Select): La requète de l'objet ou de l'identifiant
            (None): Aucun object trouvé.

        Raises:
            errors.SidbNotFoundError: Si aucun territoire n'a pu être trouvé avec ces critères.
            ValueError: Si les critères de recherche sont mauvais.
        """
        # :todo: Implémenter gestion des paramètres scale, is_in, is_like
        return self.get_mtobject_tap(Territory,
                                     *args,
                                     like_value=like_value,
                                     ignore_case=ignore_case,
                                     ignore_accent=ignore_accent,
                                     return_type=return_type,
                                     raise_none=raise_none,
                                     multi=multi,
                                     verbose=verbose,
                                     **kwargs)

    def get_territories(self,
                        *args,
                        like_value: bool = False,
                        ignore_case: bool = False,
                        ignore_accent: bool = False,
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
                        verbose: bool = False,
                        ) -> list[Territory] | list[int] | int | Select:
        """ Trouve plusieurs territoires.

        Args:
            *args: Duo d'arguments "NomDeProprieté", "Valeur"
            like_value: Si True, la valeur est recherchée à travers
                l'[instruction LIKE de SQL](https://www.postgresql.org/docs/current/functions-matching.html#FUNCTIONS-LIKE)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            ignore_case: Recherche ignorant la casse.
            ignore_accent: Recherche ignorant l'accentuation.
            map_id: Filtre d'identifiants des objets.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets `Territory`.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            cache_properties: Liste de propriétés à mettre en cache.
            verbose: Si True, est bavard.

        Returns:
            (list[Territory]): Liste des territoires recherchés.
            (list[int]): List des identifiants des territoires recherchés.
            (int): Nombre de territoires correspondants aux arguments donnés.
            (Select): Requète des objets.

        Raises:
            ValueError: Paramètres invalides.
        """
        # FutureDev: Ajouter l'option "source_ref" pour selectionner les source_ref

        return self.get_mtobjects_tap(Territory,
                                      *args,
                                      like_value=like_value,
                                      ignore_case=ignore_case,
                                      ignore_accent=ignore_accent,
                                      map_id=map_id,
                                      return_type=return_type,
                                      cache_properties=cache_properties,
                                      verbose=verbose)

    def get_territories_in(self,
                           territory: Territory,
                           scale: str | None = None,
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
                           ) -> list[Territory] | list[int] | int | Select:
        """Trouve des territoires contenus dans un territoire.

        Args:
            territory: L'object `Territory` contenant les territoires voulus.
            scale: Échelle de recherche.
            self_include: Inclure ou non l'élément passé en paramètre.
            cache_properties: Liste des propriétés à mettre en cache.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            verbose: Si True, est bavard.

        Returns:
            (list[Territory]): Liste des objets contenus dans l'objet passé en paramètre.
            (list[int]): Liste des identifiants des objets contenus dans l'objet passé en paramètre.
            (int): Nombre d'objets contenus dans l'objet passé en paramètre.
            (Select): Requète des territoires ou des identifiants.
        """
        return self.get_mtobjects_tap_in(territory,
                                         Territory,
                                         scale=scale,
                                         self_include=self_include,
                                         cache_properties=cache_properties,
                                         return_type=return_type,
                                         verbose=verbose)

    def get_territories_on(self,
                           territory: Territory,
                           scale: str | None = None,
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
                           ) -> list[Territory] | list[int] | int | Select:
        """Trouve des territoires contenant le territoire.

        Args:
            territory: L'object `Territory` contenu dans les territoires
                recherchés.
            scale: L'échelle des territoires recherchés (commune, pays...).
            self_include: Si True, inclu le territoire d'origine dans le résultat.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.

        Returns:
            (list[Territory]): Liste des objets contenus dans l'objet passé en paramètre.
            (list[int]): Liste des identifiants des objets contenus dans l'objet passé en paramètre.
            (int): Nombre d'objets contenus dans l'objet passé en paramètre.
            (Select): Requète des territoires ou des identifiants.
        """
        return self.get_mtobjects_tap_on(territory,
                                         Territory,
                                         scale=scale,
                                         self_include=self_include,
                                         cache_properties=cache_properties,
                                         return_type=return_type)

    def get_all_territories_like_name_code(self,
                                           name_code: str,
                                           cache_properties: list[str] = [],
                                           return_type: Literal['list',
                                                                'object',
                                                                'id',
                                                                'query',
                                                                'queryid',
                                                                'qid',
                                                                'count',
                                                                ] = 'list',
                                           ) -> list[Territory] | list[int] | int | Select:
        """Trouve les territoires contenant `name_code` dans leurs noms ou codes.

        Args:
            name_code: Chaîne de caractère recherchée.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.

        Returns:
            (list[Territory]): Liste des territoires correspondants.
            (list[int]): List des identifiants des territoires correspondants.
            (int): Nombre de territoires correspondants.
            (Select): Requète des territoires ou des identifiants.
        """
        q = {}
        for nq, targetq in zip(["id", "object"], [Territory.id, Territory]):
            q[nq] = select(targetq)
            q[nq] = q[nq].join(Territory.properties)
            q[nq] = q[nq].where(or_(func.unaccent(Property.value_literal)
                                        .icontains(func.unaccent(name_code)),
                                    func.unaccent(Property.value_literal)
                                        .icontains(func.unaccent(name_code.replace("-", " "))),
                                    func.unaccent(Property.value_literal)
                                        .icontains(func.unaccent(name_code.replace(" ", "-")))
                                    )
                                )
            q[nq] = q[nq].where(or_(Property.name_a == "Name",
                                    Property.name_a == "NameAlias",
                                    Property.name_a == "Code",
                                    Property.name_a == "CodeAlias"
                                    )
                                )
        result = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return result

    def get_territory_scales(self) -> list[str]:
        """Renvoie la liste des différentes échelles des territoires."""
        stmt = select(Property.value_literal).filter_by(name_a='Scale').distinct()
        return self.session.scalars(stmt).all()

    def load_territory(self, mapper: Mapper, verbose: bool = False) -> None:
        """Charge un territoire et ses propriétés dans la base de données.

        Args:
            mapper: Le mapper contenant les informations du territoire.
            verbose:
        """
        territory = None
        if mapper.primary_key != -1:
            i_primary_keys = [i for i, pk in enumerate(mapper.primary_keys) if pk]
            for ipk in i_primary_keys:
                mapper_ipk = mapper.get_dict_i(ipk)
                territory = self.get_territory(mapper_ipk["key"], mapper_ipk["value"], raise_none=False)
                if territory is not None:
                    break
        else:
            lst_i_keys = mapper.get_keys_index("Code", startswith=True)
            lst_i_keys += mapper.get_keys_index("Name", startswith=True)
            for ikey in lst_i_keys:
                dict_key = mapper.get_dict_i(ikey)
                territory = self.get_territory(dict_key["key"], dict_key["value"], raise_none=False)
                if territory is not None:
                    break

        new_territory = False
        if territory is None:
            territory = Territory()
            self.session.add(territory)
            new_territory = True

        territory.delete_cached_properties()
        # Tous les attributs non spécifiques
        territory.set_extra_properties(mapper)
        # Tous les attributs spécifiques
        result = {}
        result["code"] = territory.set_code(mapper)
        result["name"] = territory.set_name(mapper)
        result["scale"] = territory.set_scale(mapper)
        result["isinterritory"] = territory.set_isin_territory(mapper)

        # Recherche des erreurs
        if result["code"][0] != "OK" and result["name"][0] != "OK":
            raise MapperError(mapper, result, "name/code")
        elif result["code"][0] != "OK" and result["code"][0] != "NO_DATA":
            raise MapperError(mapper, result, "code")
        elif result["name"][0] != "OK" and result["name"][0] != "NO_DATA":
            raise MapperError(mapper, result, "name")
        if new_territory and result["scale"][0] != "OK":
            raise MapperError(mapper, result, "scale")
        if result["isinterritory"][0] != "OK" and result["isinterritory"][0] != "NO_DATA":
            raise MapperError(mapper, result, "isinterritory")

    # Actor
    def get_actor(self,
                  *args,
                  like_value: bool = False,
                  ignore_case: bool = False,
                  ignore_accent: bool = False,
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
                  **kwargs
                  ) -> Actor | int | Select | None:
        """Trouve un acteur.

        Examples:
            >>> actor = get_actor(id=487)
            >>> actor = get_actor("Id", 487)

        Args:
            *args: Duo d'arguments "NomDeProprieté", "Valeur", ou chaîne-objet "Actor(Code=xxxxx)", ou vide si kwargs renseignés
            **kwargs: code=="xxxxx" ou code_siret="xxxxx" ou name="xxxxxx" ou name_fr="xxxxx"
            like_value: Si True, la valeur est recherchée à travers
                l'[instruction LIKE de SQL](https://www.postgresql.org/docs/current/functions-matching.html#FUNCTIONS-LIKE)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            ignore_case: Recherche ignorant la casse.
            ignore_accent: Recherche ignorant l'accentuation.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `object`: L'objet `Actor`.
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
            verbose: Si True, est bavard.

        Returns:
            (Actor): L'object trouvé.
            (int): L'identifiant de l'objet trouvé.
            (Select): La requète de l'objet ou de l'identifiant
            (None): Aucun object trouvé.

        Raises:
            errors.SidbNotFoundError: Si aucun acteur n'a pu être trouvé avec ces critères.
            ValueError: Si les critères de recherche sont mauvais.
        """
        return self.get_mtobject_tap(Actor,
                                     *args,
                                     like_value=like_value,
                                     ignore_case=ignore_case,
                                     ignore_accent=ignore_accent,
                                     return_type=return_type,
                                     raise_none=raise_none,
                                     multi=multi,
                                     verbose=verbose,
                                     **kwargs)

    def get_actors(self,
                   *args,
                   like_value: bool = False,
                   ignore_case: bool = False,
                   ignore_accent: bool = False,
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
                   verbose: bool = False,
                   ) -> list[Actor] | list[int] | int | Select:
        """Trouve plusieurs acteurs.

        Examples:
            >>> actors = get_actors("Name", "Michel")
            >>> all_actors = get_actors()

        Args:
            *args: Duo d'arguments "NomDeProprieté", "Valeur"
            like_value: Si True, la valeur est recherchée à travers
                l'[instruction LIKE de SQL](https://www.postgresql.org/docs/current/functions-matching.html#FUNCTIONS-LIKE)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            ignore_case: Recherche ignorant la casse.
            ignore_accent: Recherche ignorant l'accentuation.
            map_id: Filtre d'identifiants des objets.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets `Actor`.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            cache_properties: Liste de propriétés à mettre en cache.
            verbose: Si True, est bavard.

        Returns:
            (list[Actor]): Liste des acteurs recherchés.
            (list[int]): List des identifiants des acteurs recherchés.
            (int): Nombre d'acteurs correspondants aux arguments donnés.
            (Select): Requète des acteurs ou des identifiants.

        Raises:
            ValueError: Paramètres invalides.
        """
        return self.get_mtobjects_tap(Actor,
                                      *args,
                                      like_value=like_value,
                                      ignore_case=ignore_case,
                                      ignore_accent=ignore_accent,
                                      map_id=map_id,
                                      return_type=return_type,
                                      cache_properties=cache_properties,
                                      verbose=verbose)

    def get_actors_in(self,
                      mtobject: Actor | Territory,
                      scale: str | None = None,
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
                      ) -> list[Actor] | list[int] | int | Select:
        """Trouve des acteurs contenus dans un territoire ou dans un autre acteur.

        Args:
            mtobject: L'object `Actor` ou `Territory` contenant des acteurs.
            scale: Échelle de recherche.
            self_include: Inclure ou non l'élément passé en paramètre.
            cache_properties: Liste des propriétés à mettre en cache.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            verbose: Si True, est bavard.

        Returns:
            (list[MTobject]): Liste des objets contenus dans l'objet passé en paramètre.
            (list[int]): List des identifiants des objets contenus dans l'objet passé en paramètre.
            (int): Nombre d'objets contenus dans l'objet passé en paramètre.
            (Select): Requète des objets.

        Raises:
            TypeError: Type de l'object non supporté.
        """
        if not isinstance(mtobject, (Actor, Territory)):
            raise TypeError(f"MTObject type '{type(mtobject)}' not supported")
        return self.get_mtobjects_tap_in(mtobject,
                                         Actor,
                                         scale=scale,
                                         self_include=self_include,
                                         cache_properties=cache_properties,
                                         return_type=return_type,
                                         verbose=verbose)

    def get_actors_on(self,
                      actor: Actor,
                      scale: str | None = None,
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
                      ) -> list[Territory] | list[int] | int | Select:
        """Trouve des acteurs contenant un autre acteur.

        Args:
            actor: L'object `Actor` contenu dans les acteurs recherchés.
            scale: Échelle de recherche.
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
            (list[Actor]): Liste des acteurs contenant l'acteur passé en paramètre.
            (list[int]): List des identifiants des objets contenus dans l'objet passé en paramètre.
            (int): Nombre d'objets contenus dans l'objet passé en paramètre.
            (Select): Requète des objets.
        """
        return self.get_mtobjects_tap_on(actor,
                                         Actor,
                                         scale=scale,
                                         self_include=self_include,
                                         cache_properties=cache_properties,
                                         return_type=return_type)

    def get_actors_by_ids(self,
                          ids: Iterable[int] | int,
                          cache_properties: list[str] = [],
                          return_type: Literal['list',
                                               'object',
                                               'query',
                                               'queryid',
                                               'qid',
                                               'count',
                                               ] = "list",
                          verbose: bool = False
                          ) -> list[Actor] | int | Select:
        """Trouve les acteurs correspondants aux identifiants.

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
            (list[Actor]): Liste des acteurs correspondants.
            (int): Nombre d'objets contenus dans l'objet passé en paramètre.
            (Select): Requète des acteurs ou des identifiants.
        """
        if isinstance(ids, int):
            ids = {ids}

        q = {}
        for nq, targetq in zip(["id", "object"], [Actor.id, Actor]):
            q[nq] = select(targetq)
            q[nq] = q[nq].where(Actor.id.in_(ids))

        result = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return result

    def get_all_actors_like_name_code(self,
                                      name_code: str,
                                      cache_properties: list[str] = [],
                                      return_type: Literal['list',
                                                           'object',
                                                           'id',
                                                           'query',
                                                           'queryid',
                                                           'qid',
                                                           'count',
                                                           ] = 'list',
                                      ) -> list[Actor] | list[int] | int | Select:
        """Trouve les acteurs contenant `name_code` dans leurs noms ou codes.

        Args:
            name_code: Chaîne de caractère recherchée.
            cache_properties: Liste des propriétés à mettre en cache,
                en plus des noms et des codes.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets correspondants.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.

        Returns:
            (list[Actor]): Liste des acteurs correspondants.
            (list[int]): List des identifiants des acteurs correspondants.
            (int): Nombre d'acteurs correspondants.
            (Select): Requète des objets ou des identifiants.
        """
        q = {}
        for nq, targetq in zip(["id", "object"], [Actor.id, Actor]):
            q[nq] = select(targetq)
            q[nq] = q[nq].join(Actor.properties)
            q[nq] = q[nq].where(or_(func.unaccent(Property.value_literal)
                                        .icontains(func.unaccent(name_code)),
                                    func.unaccent(Property.value_literal)
                                        .icontains(func.unaccent(name_code.replace("-", " "))),
                                    func.unaccent(Property.value_literal)
                                        .icontains(func.unaccent(name_code.replace(" ", "-")))
                                    )
                                )
            q[nq] = q[nq].where(or_(Property.name_a == "Name",
                                    Property.name_a == "NameAlias",
                                    Property.name_a == "Code",
                                    Property.name_a == "CodeAlias"
                                    )
                                )
        result = self.compute_query_return_type(q, return_type)
        self.compute_query_cache_properties(cache_properties, return_type, q['id'])
        return result

    def load_actor(self, mapper: Mapper, verbose: bool = False) -> None:
        """Charge un acteur et ses propriétés dans la base de données.

        Args:
            mapper: Le mapper contenant les informations de l'acteur.
            verbose:
        """
        actor = None
        if mapper.primary_key != -1:
            i_primary_keys = [i for i, pk in enumerate(mapper.primary_keys) if pk]
            for ipk in i_primary_keys:
                mapper_ipk = mapper.get_dict_i(ipk)
                actor = self.get_actor(mapper_ipk["key"], mapper_ipk["value"], raise_none=False)
                if actor is not None:
                    break
        else:
            lst_i_keys = mapper.get_keys_index("Code", startswith=True)
            lst_i_keys += mapper.get_keys_index("Name", startswith=True)
            for ikey in lst_i_keys:
                dict_key = mapper.get_dict_i(ikey)
                if dict_key["value"] != dict_key["value"].strip():
                    print(f"WARNING : space at beginning / end in code {dict_key['key']}:"
                          f"'{dict_key['value']}' - this might be unwanted")
                actor = self.get_actor(dict_key["key"], dict_key["value"], raise_none=False)
                if actor is not None:
                    break

        if actor is None:
            actor = Actor()
            self.session.add(actor)

        actor.delete_cached_properties()

        actor.set_extra_properties(mapper)
        result = {}
        result["code"] = actor.set_code(mapper)
        result["name"] = actor.set_name(mapper)
        result["isinactor"] = actor.set_isin_actor(mapper)
        result["isinterritory"] = actor.set_isin_territory(mapper)
        result["territory"] = actor.set_territory(mapper)
        result["emitteractor"] = actor.set_emitter_actor(mapper)
        result["scale"] = actor.set_scale(mapper)

        # Recherche des erreurs
        if result["code"][0] != "OK" and result["code"][0] != "NO_DATA":
            raise MapperError(mapper, result, "code")
        if result["name"][0] != "OK" and result["name"][0] != "NO_DATA":
            raise MapperError(mapper, result, "name")
        if result["isinactor"][0] != "OK" and result["isinactor"][0] != "NO_DATA":
            raise MapperError(mapper, result, "isinactor")
        if result["territory"][0] != "OK" and result["territory"][0] != "NO_DATA":
            raise MapperError(mapper, result, "territory")

    # Product
    def get_product(self,
                    *args,
                    nomenclature: str | None = None,
                    like_value: bool = False,
                    ignore_case: bool = False,
                    ignore_accent: bool = False,
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
                    **kwargs
                    ) -> Product | int | Select | None:
        """Trouve un produit.

        Args:
            *args: Duo d'arguments "NomDeProprieté", "Valeur", ou chaîne-objet "Product(Code=xxxxx)", ou vide si kwargs renseignés
            **kwargs: code=="xxxxx" ou name="xxxxxx" ou name_fr="xxxxx"
            like_value: Si True, la valeur est recherchée à travers
                l'[instruction LIKE de SQL](https://www.postgresql.org/docs/current/functions-matching.html#FUNCTIONS-LIKE)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            nomenclature: Nom de la nomenclature du produit recherché.
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            ignore_case: Recherche ignorant la casse.
            ignore_accent: Recherche ignorant l'accentuation.
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

        Returns:
            (Product): L'object trouvé (ou une liste si multi=list)
            (int): L'identifiant de l'objet trouvé (ou une liste si multi=list)
            (Select): La requète de l'objet ou de l'identifiant
            (None): Aucun object trouvé.

        Raises:
            errors.SidbNotFoundError: Aucun produit n'a pu être trouvé avec ces critères.
            ValueError: Si les critères de recherche sont mauvais.

        """

        #FutureDev : Implementer l'option "use_alias" (True par design)
        return self.get_mtobject_tap(Product,
                                     *args,
                                     nomenclature=nomenclature,
                                     like_value=like_value,
                                     ignore_case=ignore_case,
                                     ignore_accent=ignore_accent,
                                     return_type=return_type,
                                     raise_none=raise_none,
                                     multi=multi,
                                     verbose=verbose,
                                     **kwargs)

    def get_products(self,
                     *args,
                     like_value: bool = False,
                     ignore_case: bool = False,
                     ignore_accent: bool = False,
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
                     ) -> list[Product] | list[int] | int | Select:
        """Trouve plusieurs produits.

        Args:
            *args: Duo d'arguments "NomDeProprieté", "Valeur"
            like_value: Si True, la valeur est recherchée à travers
                l'[instruction LIKE de SQL](https://www.postgresql.org/docs/current/functions-matching.html#FUNCTIONS-LIKE)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            ignore_case: Recherche ignorant la casse.
            ignore_accent: Recherche ignorant l'accentuation.
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
                                      ignore_case=ignore_case,
                                      ignore_accent=ignore_accent,
                                      map_id=map_id,
                                      return_type=return_type,
                                      cache_properties=cache_properties,
                                      nomenclature=nomenclature,
                                      verbose=verbose)

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

        Returns:
            (list[Product]): Liste des produits recherchés.
            (list[int]): List des identifiants des produits recherchés.
            (int): Nombre de produits correspondants aux arguments donnés.
            (Select): Requète des produits ou des identifiants.
        """
        return self.get_mtobjects_tap(Product,
                                      "Nomenclature",
                                      nomenclature,
                                      return_type=return_type,
                                      cache_properties=cache_properties,
                                      nomenclature=nomenclature,
                                      verbose=verbose)

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
        """

        # FutureDev:  Améliorer Prototype
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
            i_primary_keys = [i for i, pk in enumerate(mapper.primary_keys) if pk]
            for ipk in i_primary_keys:
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

    # Stock
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
                   source_ref: str | None = None,
                   filter_by: list[tuple[str, str]] = [],
                   target_join_or: bool = True,
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
            source_ref: La source de référence des stocks.
            filter_by: Liste de propriétés supplémentaires pour le filtrage des
                stocks (ex. [("Label", "Bio")]).
            target_join_or: Si `True`, compare les `target` en utilisant un ou binaire,
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


        """
        #Note: FutureDev Implementer target_(asc/desc).

        return self.get_mtobjects_gs(Stock, target=target, product=product,
                                     product_asc=product_asc,
                                     product_desc=product_desc, date_point=date_point,
                                     date_start=date_start, date_end=date_end,
                                     year=year, month=month, source_ref=source_ref,
                                     filter_by=filter_by,
                                     target_join_or=target_join_or,
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

    # Gateflow
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
                      source_ref: str | None = None,
                      filter_by: list[tuple[str, str]] = [],
                      target_join_or: bool = True,
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
            source_ref: La source de référence des flux.
            filter_by: Liste de propriétés supplémentaires pour le filtrage des
                flux (ex. [("Label", "Bio")]).
            target_join_or: Si `True`, compare les `target` en utilisant un ou binaire,
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
        """
        # Note: FutureDev - Implementer target_(asc / desc).
        return self.get_mtobjects_gs(Gateflow, target=target, flowtype=flowtype,
                                     product=product, product_asc=product_asc,
                                     product_desc=product_desc, date_point=date_point,
                                     date_start=date_start, date_end=date_end,
                                     year=year, month=month, source_ref=source_ref,
                                     filter_by=filter_by,
                                     target_join_or=target_join_or,
                                     map_id=map_id,
                                     cache_properties=cache_properties,
                                     return_type=return_type, verbose=verbose)

    def get_inputs(self,
                   target: list[Territory | Actor] = [],
                   **kwargs
                   ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux d'entrée de `target`.

        Fonction wrapper de [get_gateflows][sidb.Sidb.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="input", **kwargs)

    def get_outputs(self,
                    target: list[Territory | Actor] = [],
                    **kwargs
                    ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux de sortie de `target`.

        Fonction wrapper de [get_gateflows][sidb.Sidb.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="output", **kwargs)

    def get_consumptions(self,
                         target: list[Territory | Actor] = [],
                         **kwargs
                         ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux de consommation de `target`.

        Fonction wrapper de [get_gateflows][sidb.Sidb.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="consumption", **kwargs)

    def get_productions(self,
                        target: list[Territory | Actor] = [],
                        **kwargs
                        ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux de production de `target`.

        Fonction wrapper de [get_gateflows][sidb.Sidb.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="production", **kwargs)

    def get_extractions(self,
                        target: list[Territory | Actor] = [],
                        **kwargs
                        ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux d'extraction de `target`.

        Fonction wrapper de [get_gateflows][sidb.Sidb.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="extraction", **kwargs)

    def get_emissions(self,
                      target: list[Territory | Actor] = [],
                      **kwargs
                      ) -> list[Gateflow] | list[int] | int | Select:
        """
        Retourne les flux d'émission de `target`.

        Fonction wrapper de [get_gateflows][sidb.Sidb.get_gateflows].
        """
        return self.get_gateflows(target, flowtype="emission", **kwargs)

    def load_gateflow(self,
                      mapper: Mapper,
                      flowtype: Literal['input', 'output',
                                        'comsumption',
                                        'production',
                                        'extraction',
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
            mapper.add("FlowType", flowtype, source_ref=mapper.all_srcref)

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

    # Pathflow
    T = TypeVar('T', Territory, Actor)

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
                      source_ref: str | None = None,
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
            btarget: Territoire ou acteur complémentaire spécifique
                (origine pour les imports, destination pour les exports)
            xtarget: Territoire ou acteur complémentaire à exclure
                (origine pour les imports, destination pour les exports).
            product: Le produit lié aux flux.
            product_asc: Effectue une recherche ascendante sur le produit
                (recherche le produit et ses parents).
            product_desc: Effectue une recherche descendante sur le produit
                (recherche le produit et ses enfants).
            date_point: La date ponctuelle des flux.
            date_start: La date de départ des flux.
            date_end: La date de fin des flux.
            year: L'année des flux.
            month: Le mois des flux.
            source_ref: La source de référence des flux.
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
        """
        # FutureDev Implementer target_(asc/desc).
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
            if source_ref is not None:
                q[nq] = q[nq].join(Pathflow.properties).where(Property.source_ref == source_ref)
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

        Fonction wrapper de [get_pathflows][sidb.Sidb.get_pathflows].
        """
        return self.get_pathflows(target, direction="import", **kwargs)

    def get_exports(self,
                    target: T | None = None,
                    **kwargs
                    ) -> list[Pathflow] | list[int] | int | Select:
        """
        Retourne les flux exportés: ceux dont l'origine est à l'intérieur de
        `target` et la destination est à l'extérieur.

        Fonction wrapper de [get_pathflows][sidb.Sidb.get_pathflows].
        """
        return self.get_pathflows(target, direction="export", **kwargs)

    def get_internals(self,
                      target: T | None = None,
                      **kwargs
                      ) -> list[Pathflow] | list[int] | int | Select:
        """
        Retourne les flux internes: ceux dont l'origine et la destination sont
        dans `target`.

        Fonction wrapper de [get_pathflows][sidb.Sidb.get_pathflows].
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

    # MTObject's common methods
    def get_mtobject_with_id(self, id: int) -> MTObject:
        """Renvoie l'objet correspondant à un identifiant."""
        return self.session.get(MTObject, id)

    def get_mtobject_tap(self,
                         mtobject_class: type[Territory | Actor | Product],
                         *args,
                         like_value: bool = False,
                         ignore_case: bool = False,
                         ignore_accent: bool = False,
                         return_type: Literal['object', 'id',
                                              'queryid', 'qid',
                                              'query'] = 'object',
                         raise_none: bool = True,
                         multi: Literal['raise', 'warn_first',
                                        'warn_list', 'first',
                                        'list'] = "warn_list",
                         nomenclature: str | None = None,
                         verbose: bool = False,
                         **kwargs
                         ) -> Territory | Actor | Product | int | Select | None:

        if mtobject_class not in [Actor, Territory, Product]:
            raise TypeError(f"mtobject_class has to be Actor, Territory or Product, got {mtobject_class}")
        if return_type not in (_list := ["object", "id", "queryid", "qid", "query"]):
            raise ValueError(f"return_type can only be one of {_list}, got {return_type}")
        if multi not in (_list := ["raise", "warn_first", "warn_list", "first", "list"]):
            raise ValueError(f"many can only be one of {_list}, got {multi}")

        key, value = Sidb.get_one_mtobject_read_kw_arg(*args, **kwargs)
        if verbose:
            print(f'key = {key}, value = {value}')

        # Recherche dans le cache si recherche sur clé exacte uniquement
        if key != "Id" and not like_value and not ignore_case and not ignore_accent:
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
                # Gestion de la casse (ignore_case) et/ou de l'accentuation (ignore_accent)
                prop = func.unaccent(Property.value_literal) if ignore_accent else Property.value_literal
                prop = func.lower(prop) if ignore_case else prop
                value = func.unaccent(value) if ignore_accent else value
                value = func.lower(value) if ignore_case else value

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
            if key != "Id" and not like_value and not ignore_case and not ignore_accent:
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
                          ignore_case: bool = False,
                          ignore_accent: bool = False,
                          map_id: Iterable[int] | int | Select = [],
                          return_type: Literal['list', 'object',
                                               'id', 'queryid', 'qid',
                                               'query', 'count'] = 'list',
                          cache_properties: list[str] = [],
                          nomenclature: str | None = None,
                          verbose: bool = False,
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
                prop = func.unaccent(Property.value_literal) if ignore_accent else Property.value_literal
                prop = func.lower(prop) if ignore_case else prop
                value = func.unaccent(value) if ignore_accent else value
                value = func.lower(value) if ignore_case else value
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
                                                  | type[Territory |
                                                         Actor |
                                                         Product]),
                             scale: str | None = None,
                             source_ref: str | None = None,
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

        if isinstance(returnmtobjecttype, str):
            returnmtobjecttype = Sidb.get_mtobjecttype_from_classname(returnmtobjecttype)

        if returnmtobjecttype not in [Actor, Territory, Product]:
            raise TypeError("'%s' is unsupported type" % returnmtobjecttype)

        if source_ref is not None:
            raise ValueError("'source_ref' argument is not defined yet. #Todo")

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
            subquery = Sidb.subquery_recursive(returnmtobjecttype,
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

        subq = Sidb.subquery_recursive_reverse(mtobject_to_return,
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
                         object_class: type[Gateflow | Stock],
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
                         source_ref: str | None = None,
                         filter_by: list[tuple[str, str]] = [],
                         target_join_or: bool = True,
                         map_id: Iterable[int] | int | Select = [],
                         cache_properties: list[str] = [],
                         return_type: Literal['list', 'object',
                                              'id', 'queryid', 'qid',
                                              'query', 'count'] = 'list',
                         verbose: bool = False
                         ) -> list[Gateflow] | list[Stock] | list[int] | int | Select:
        """
        Fonction générique pour récupérer des gateflows ou des stocks
        """
        # FutureDev: Implementer target_(asc/desc).

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
            if source_ref is not None:
                q[nq] = (q[nq].join(object_class.properties)
                         .where(Property.source_ref == source_ref)
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
                if target_join_or:
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

    # Static functions
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
        """
        # FutureDev : Implémenter profondeur.
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
        """
        #  FutureDev:  Implémenter profondeur.
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
