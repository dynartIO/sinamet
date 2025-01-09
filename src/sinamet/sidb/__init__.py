from __future__ import annotations

from typing import Literal, Any

from collections.abc import Iterable, Iterator

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, object_session
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.sql import select, or_, and_, delete, func, Select

from sinamet.sidb.mtobject import SidbMTObject
from sinamet.sidb.territory import SidbTerritory
from sinamet.sidb.actor import SidbActor
from sinamet.sidb.product import SidbProduct
from sinamet.sidb.gateflow import SidbGateflow
from sinamet.sidb.pathflow import SidbPathflow
from sinamet.sidb.stock import SidbStock

from sinamet.core.config import config
from sinamet.core.mapper import Mapper, MapperError

from sinamet.mtobjects.dbobject import DBObjectClassBase
from sinamet.mtobjects.mtobject import MTObject
from sinamet.mtobjects.property import Property
from sinamet.mtobjects.territory import Territory
from sinamet.mtobjects.actor import Actor
from sinamet.mtobjects.product import Product
from sinamet.mtobjects.pathflow import Pathflow
from sinamet.mtobjects.gateflow import Gateflow
from sinamet.mtobjects.stock import Stock


class Sidb(SidbMTObject,
           SidbTerritory,
           SidbActor,
           SidbProduct,
           SidbGateflow,
           SidbPathflow,
           SidbStock):
    sessionmakers: dict[str, sessionmaker] = {}
    sessions: list[Sidb] = []

    def __init__(self, session: Session):
        self.session: Session = session
        self.cache: dict[tuple[str, str, str], MTObject] = {}

    @contextmanager
    def connect(autocommit: bool = True,
                verbose: bool = False,
                **kwargs) -> Iterator[Sidb]:
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
            db_path = config.init_db(verbose=verbose, **kwargs)
            engine = create_engine(db_path)
            DBObjectClassBase.metadata.create_all(engine)
            Session = sessionmaker(engine)
            Sidb.sessionmakers[config.current_environref] = Session
        elif verbose:
            print(f"Found a sessionmaker for {config.current_environref=}.")
        session = Session()
        try:
            sidb = Sidb(session)
            Sidb.sessions.append(sidb)
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
        """Charge un objet dans la base de donnée.

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

    def delete_sourceref(self,
                         sourceref: str,
                         exclude: str | list[str] = [],
                         recursive: bool = False) -> None:
        """Supprime une source de référence.

        Supprime une source de référence en supprimant les propriétés qui lui sont liées.

        Parameters:
            sourceref: La source de référence à supprimer.
            exclude: Liste de noms de propriétés à ne pas supprimer.
            recursive: Si `True`, supprime également les sources enfants de `sourceref`.
        """
        if isinstance(exclude, str):
            exclude = (exclude,)

        delete_stmt = delete(Property).where(Property.name_a.not_in(exclude))
        if recursive:
            delete_stmt = delete_stmt.where(
                    (Property.sourceref.startswith(f'{sourceref}:'))
                    | (Property.sourceref == sourceref)
            )
        else:
            delete_stmt = delete_stmt.where(
                    Property.sourceref == sourceref
            )
        self.session.execute(delete_stmt)

        # Delete MTObjects without any properties left.
        self.session.execute(
                delete(MTObject)
                .where(~MTObject.properties.any())
        )

    def get_sourcerefs(self, subinclude: bool = True) -> list[str]:
        """Renvoie toutes les sources des propriétés enregistrées.

        Parameters:
            subinclude: Inclut la décomposition des noms des sources selon ":"
                ex: source:nom1:nom2 => [source, source:nom1, source:nom1:nom2]

        Returns:
            La liste des sources des propriétés.
        """
        src_lst = self.session.scalars(
                select(Property.sourceref).distinct()
                ).all()
        if not subinclude:
            return sorted(src_lst)
        temp_add = []
        for src in src_lst:
            temp = src.split(":")
            temp_compo = ""
            for substr in temp:
                temp_compo += substr
                if temp_compo not in src_lst and temp_compo not in temp_add:
                    temp_add.append(temp_compo)
                temp_compo += ":"
        src_lst += temp_add
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
        stats = {}
        lstobjecttype = [Territory, Product, Actor, Stock, Gateflow, Pathflow, Property]
        for obj in lstobjecttype:
            stats[f"nb-mtobject-{obj.__tablename__}"] = self.session.scalar(
                                                            select(func.count(obj.id))
                                                        )
        stats["nomenclatures"] = self.get_list_nomenclatures()
        stats["scales"] = self.get_territory_scales()

        for sc in stats["scales"]:
            stmt = (select(func.count(Territory.id))
                    .join(Territory.properties)
                    .where((Property.name_a == 'Scale')
                           & (Property.value_literal == sc)))
            stats["nb-scale-" + sc.lower()] = self.session.scalar(stmt)

        stats["sourcerefs"] = self.get_sourcerefs(False)
        stats["propertyname"] = [f"{a}{'' if b is None else f'@{b}'}"
                                 for a, b in self.session.execute(
                                     select(Property.name_a, Property.name_b)
                                     .distinct()
                                     ).all()
                                 ]
        stats["sourcerefname"] = self.session.scalars(
                select(Property.sourceref).distinct()
                ).all()
        return stats

    def get_properties(self, properties: Iterable[str] | str,
                       map_id: Select | list[int] = None,
                       startlike: bool = False,
                       return_type: str = 'list') -> list[Property]:
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
        mysqllst = []
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
                                  ) -> Select | list[Any] | int:
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
                        select(func.count()).select_from(qnq['id'].distinct())
                )
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

    def get_distinct_property_values(self, prop_name: str) -> list[str]:
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

    def is_loaded(self, sourceref: str) -> bool:
        """Détermine si une source est chargée.

        Parameters:
            sourceref: Le nom de la source à vérifier.

        Returns:
            `True` si la source est déjà chargée dans la base de donnée,
                `False` sinon.
        """
        return sourceref in self.get_sourcerefs(False)

    def is_not_loaded(self, sourceref: str) -> bool:
        """Détermine si une source n'est pas chargée.

        Parameters:
            sourceref: Le nom de la source à vérifier.

        Returns:
            `True` si la source n'est pas chargée dans la base de donnée,
                `False` sinon.
        """
        return sourceref not in self.get_sourcerefs(False)

    def progress(self, steps_commit: int = 1000,
                 steps_print: int = 20, commit: bool = True) -> None:
        """Acte des changements.

        Cette fonction permet de suivre l'importation de données, en affichant
        la progression dans le shell, et en commitant les transactions.

        Parameters:
            steps_commit: Le nombre d'appel entre chaque commit.
            steps_print: Le nombre d'appel entre chaque affichage dans le shell.
            commit: Commit ou non.
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
        engine = self.session.bind
        engine.dispose()
        DBObjectClassBase.metadata.drop_all(engine)

    def reset(self) -> None:
        """
        Ferme la session, supprime les tables de la base de donnée puis les
        recrée.
        """
        self.drop_all()
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
