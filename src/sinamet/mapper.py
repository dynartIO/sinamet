from __future__ import annotations

import typing
from typing import Any

import warnings

from sinamet.tools.timext import get_start_end_dates, to_date

if typing.TYPE_CHECKING:
    from datetime import date, datetime
    from shapely import Geometry
    from sinamet.mtobjects.mtobject import MTObject


class Mapper():
    def __init__(self,
                 type: str,
                 source_ref: str | None = None
                 ) -> None:
        """Constructeur du Mapper.

        Parameters:
            type: Le type d'objet lié au Mapper (Territory, Actor, ...)
            source_ref: La source de référence de l'objet.
        """
        self.type: str = type.lower()

        self.keys: list[str] = []
        self.values: list[str | MTObject | Geometry] = []
        self.date_start: list[date | None] = []
        self.date_end: list[date | None] = []
        self.date_point: list[date | None] = []
        self.source_refs: list[str | None] = []
        self.foreign_keys: list[bool] = []
        self.primary_keys: list[bool] = []
        self.unique: list[bool] = []

        self.primary_key: int = -1
        self.all_srcref: str | None = source_ref

    def __str__(self) -> str:
        st = "MAPPER : Type " + self.type + " ------------\n"
        for key, val, ds, de, dp, src in zip(self.keys, self.values, self.date_start, self.date_end,
                                             self.date_point, self.source_refs):
            st += key + " --> " + str(val)

            if ds is not None or de is not None:
                st += f" [{ds} -> {de}]"
            if dp is not None:
                st += f" [{dp}]"
            if src is not None:
                st += f" {{src={src}}}"
            if self.all_srcref is not None:
                st += f" {{src={self.all_srcref}}}"
            st += "\n"
        st += "--------------------------\n"
        return st

    def __len__(self) -> int:
        return len(self.keys)

    def get_dict_key(self, key: str) -> dict[str, str] | None:
        """Récupère le dictionnaire contenant les informations d'une clé.

        Parameters:
            key: La clé, qui est également le nom de la propriété de l'objet.

        Returns:
            Si la clé éxiste, le dictionnaire contenant les informations liées à
                la clé, renvoyé par [get_dict_i][mapper.Mapper.get_dict_i].
                Sinon, renvoie `None`

        Raises:
            ValueError: Plusieurs clés correspondent.
        """
        c = self.keys.count(key)
        if c == 0:
            return None
        elif c == 1:
            return self.get_dict_i(self.keys.index(key))
        else:
            raise ValueError(f"Several corresponding key '{key}'"
                             "have been found. Only one was expected.")

    def get_dict_i(self, index: int) -> dict[str, Any]:
        """Renvoie le dictionnaire correspondant à un index.

        Parameters:
            index: L'index correspondant aux informations que l'on souhaite
                récupérer.

        Returns:
            Un dictionnaire contenant:

                - `key`: Le nom complet de la propriété.
                - `value`: La valeur de la propriété.
                - `type_value`: *À implémenter*
                - `date_start`: Date de début de la propriété.
                - `date_end`: Date de fin de la propriété.
                - `date_point`: Date de la propriété.
                - `unique`: Si la propriété, doit être unique pour l'objet.
                - `source_ref`: La source de référence de la propriété.
        """
        dic: dict[str, Any] = {}
        dic["key"] = self.keys[index]
        dic["value"] = self.values[index]
        dic["type_value"] = None  # :todo: Implementation ???
        dic["date_start"] = self.date_start[index]
        dic["date_end"] = self.date_end[index]
        dic["date_point"] = self.date_point[index]
        dic["unique"] = self.unique[index]
        if self.source_refs[index] is not None:
            dic["source_ref"] = self.source_refs[index]
        elif self.all_srcref is not None:
            dic["source_ref"] = self.all_srcref
        else:
            dic["source_ref"] = None
        return dic

    def get(self,
            key: str,
            default: Any | None = None) -> Any:
        """Retourne la valeur associée à une clé.

        Parameters:
            key: Clé à rechercher.
            default: Valeur à retourner si la clé n'est pas connue.

        Note: FutureDev
            Uniquement la première valeur du tableau. Implémenter la gestion de clefs multiples
        """
        try:
            return self.values[self.keys.index(key)]
        except ValueError:
            return default

    def get_keys_index(self,
                       key: str,
                       startswith: bool = False,
                       alias: bool = False,
                       exact: bool = True) -> list[int]:
        """Récupère la liste des indexs correspondants à la clé.

        Parameters:
            key: La clé à rechercher.
            startswith:
            alias:
            exact:

        Returns:
            La liste des indexs correspondants.
        """
        lst_key: list[int] = []
        for index, k in enumerate(self.keys):
            if k == key and exact:
                lst_key.append(index)
                continue
            if startswith and k.startswith(key + "@"):
                lst_key.append(index)
                continue
            spec_word = ["Code", "Name", "CodeAlias", "NameAlias"]
            tbl_spec = [key + w for w in spec_word]
            if startswith and (k.split("@")[0] in tbl_spec):
                lst_key.append(index)
                continue
            if alias and k == key + "Alias" and exact:
                lst_key.append(index)
                continue
            if alias and startswith and k.startswith(key + "Alias@"):
                lst_key.append(index)
                continue
        return lst_key

    def add(self, key: str,
            value: str | MTObject | Geometry,
            date_point: str | date | datetime | None = None,
            date_start: str | date | datetime | None = None,
            date_end: str | date | datetime | None = None,
            year: str | int | None = None,
            month: str | int | None = None,
            source_ref: str | None = None,
            primary_key: bool = False,
            foreign_key: bool = False,
            unique: bool = False,
            ) -> None:
        """Ajoute une propriété au Mapper.

        Parameters:
            key: Le nom de la propriété.
            value: La valeur de la propriété.
            date_point: La date de la propriété.
            date_start: La date de début de la propriété.
            date_end: La date de fin de la propriété.
            year: L'année de la propriété.
            month: Le mois de la propriété.
            source_ref: La source de référence de la propriété.
            primary_key: Indique si la propriété est une
                [clé primaire](../quickstart/indepth.md#cles-primaires-et-etrangeres)
                (uniquement pour les `Code` ou `Name`)
            foreign_key: Indique si la propriété est une
                [clé étrangère](../quickstart/indepth.md#cles-primaires-et-etrangeres)
                (uniquement pour les `Code` ou `Name`)
            unique: Vérifie l'unicité de la propriété avant de l'associer au MTObject
                (En développement).
        """
        # To depreciate
        if key == "SourceRef":
            raise ValueError("SourceRef is not an available key at the moment.")

        if key.startswith("Primary:") or primary_key:
            if key.startswith("Primary:"):
                key = key.replace("Primary:", "", 1)
                warnings.warn("Deprecated use of 'Primary:' in direct Mapper args name."
                              " Use attribute 'primary_key=' instead")
                primary_key = True
            self.primary_key = len(self)

        if (primary_key or foreign_key) and not key.startswith(('Code', 'Name')):
            raise ValueError("`primary_key` can only be associated with Code or Name")
        if primary_key and foreign_key:
            raise ValueError('Cannot have `primary_key` and `foreign_key`'
                             ' at the same time.')

        date_point = to_date(date_point)
        start_n, end_n = get_start_end_dates(start=date_start, end=date_end,
                                             year=year, month=month)
        if (start_n, end_n) == get_start_end_dates():
            start_n, end_n = None, None

        if start_n is not None and end_n is not None and date_point is not None:
            raise AttributeError("Too many information about date (start, end)+(point)")

        self.keys.append(key)
        self.values.append(value)
        self.date_start.append(start_n)
        self.date_end.append(end_n)
        self.date_point.append(date_point)
        self.source_refs.append(source_ref)
        self.unique.append(unique)
        self.primary_keys.append(primary_key)
        self.foreign_keys.append(foreign_key)

    def is_foreign_key(self, keyindex: int) -> bool:
        """Détermine si la propriété à un certain index est une clé étrangére."""
        return self.foreign_keys[keyindex]

    def is_primary_key(self, keyindex: int) -> bool:
        """Détermine si la propriété à un certain index est une clé primaire."""
        return self.primary_key == keyindex


class MapperError(Exception):
    def __init__(self,
                 mapper: Mapper,
                 result: dict[str, str],
                 key: str
                 ) -> None:
        self.mapper = mapper
        self.result = result
        self.key = key
        print("--------- ERROR CONTEXT : MAPPER ----------------")
        print(mapper)
        print("--------- ERROR CONTEXT : RESULT ----------------")
        print(result)
        print()
        try:
            msg = "Wrong data associated with key '%s', error info = %s" % (key, result[key])
        except KeyError:
            msg = "Unknown error '%s'" % (key)
        super().__init__(msg)
