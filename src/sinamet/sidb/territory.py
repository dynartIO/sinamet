from typing import Literal, Iterable

from sqlalchemy import or_
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import Select

from sinamet.mtobjects.territory import Territory
from sinamet.mtobjects.property import Property
from sinamet.core.mapper import Mapper, MapperError


class SidbTerritory:
    def get_territory(self,
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
                      ) -> Territory | int | Select | None:
        """Trouve un territoire.

        Examples:
            >>> territory = get_territory(code="16")
            >>> territory = get_territory("Name", "Saint-%", like_value=True)

        Args:
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            case_value: Recherche sensible à la casse.
            accent_value: Recherche sensible à l'accentuation.
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
            deep_verbose: Si True, est plus bavard.

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
                                     case_value=case_value,
                                     accent_value=accent_value,
                                     return_type=return_type,
                                     raise_none=raise_none,
                                     multi=multi,
                                     verbose=verbose,
                                     deep_verbose=deep_verbose,
                                     **kwargs)

    def get_territories(self,
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
                        ) -> list[Territory] | list[int] | int | Select:
        """ Trouve plusieurs territoires.

        Args:
            like_value: Si True, compare la valeur passée avec LIKE à la place de l'égalité (=)
                (les charactères spéciaux `%` et `_` ne seront pas échappés).
            case_value: Recherche sensible à la casse.
            accent_value: Recherche sensible à l'accentuation.
            map_id: Filtre d'identifiants des objets.
            return_type: Type de retour de la fonction. Valeurs possibles:

                * `list` ou `object`: La liste des objets `Territory`.
                * `id`: La liste des identifiants des objets.
                * `query`: La requète des objets.
                * `queryid` ou `qid`: La requète des identifiants des objects.
                * `count`: Nombre d'éléments correspondants.
            cache_properties: Liste de propriétés à mettre en cache.
            verbose: Si True, est bavard.
            deep_verbose: Si True, est plus bavard.

        Returns:
            (list[Territory]): Liste des territoires recherchés.
            (list[int]): List des identifiants des territoires recherchés.
            (int): Nombre de territoires correspondants aux arguments donnés.
            (Select): Requète des objets.

        Raises:
            ValueError: Paramètres invalides.

        FutureDev:
            Ajouter l'option "sourceref" pour selectionner les sourceref
        """
        return self.get_mtobjects_tap(Territory,
                                      *args,
                                      like_value=like_value,
                                      case_value=case_value,
                                      accent_value=accent_value,
                                      map_id=map_id,
                                      return_type=return_type,
                                      cache_properties=cache_properties,
                                      verbose=verbose,
                                      deep_verbose=deep_verbose)

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
            iprimarykeys = [i for i, pk in enumerate(mapper.primarykeys) if pk]
            for ipk in iprimarykeys:
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
