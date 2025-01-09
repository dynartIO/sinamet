from typing import Literal
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import Select

from sinamet.mtobjects.actor import Actor
from sinamet.mtobjects.territory import Territory
from sinamet.mtobjects.property import Property
from sinamet.core.mapper import Mapper, MapperError


class SidbActor:
    def get_actor(self,
                  *args,
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
                  ) -> Actor | int | Select | None:
        """Trouve un acteur.

        Examples:
            >>> actor = get_actor(id=487)
            >>> actor = get_actor("Id", 487)

        Args:
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            case_value: Recherche sensible à la casse.
            accent_value: Recherche sensible à l'accentuation.
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
            deep_verbose: Si True, est plus bavard.

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
                                     case_value=case_value,
                                     accent_value=accent_value,
                                     return_type=return_type,
                                     raise_none=raise_none,
                                     multi=multi,
                                     verbose=verbose,
                                     deep_verbose=deep_verbose,
                                     **kwargs)

    def get_actors(self,
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
                   verbose: bool = False,
                   deep_verbose: bool = False
                   ) -> list[Actor] | list[int] | int | Select:
        """Trouve plusieurs acteurs.

        Examples:
            >>> actors = get_actors("Name", "Michel")
            >>> all_actors = get_actors()

        Args:
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            case_value: Recherche sensible à la casse.
            accent_value: Recherche sensible à l'accentuation.
            map_id: Filtre d'identifiants des objets.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets `Actor`.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            cache_properties: Liste de propriétés à mettre en cache.
            verbose: Si True, est bavard.
            deep_verbose: Si True, est plus bavard.

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
                                      case_value=case_value,
                                      accent_value=accent_value,
                                      map_id=map_id,
                                      return_type=return_type,
                                      cache_properties=cache_properties,
                                      verbose=verbose,
                                      deep_verbose=deep_verbose)

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
            iprimarykeys = [i for i, pk in enumerate(mapper.primarykeys) if pk]
            for ipk in iprimarykeys:
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
