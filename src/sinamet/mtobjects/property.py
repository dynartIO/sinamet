from __future__ import annotations

import typing
from typing import Optional

from datetime import datetime, date

import numpy

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape

from shapely.geometry import (Point,
                              Polygon,
                              MultiPolygon,
                              LineString,
                              MultiLineString,
                              MultiPoint)

from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import reconstructor

from sinamet.tools.timext import to_date

from .dbobject import DBObjectClassBase

if typing.TYPE_CHECKING:
    from .mtobject import MTObject


class Property(DBObjectClassBase):
    """Objet Property"""
    dictoftypes: dict[str, int] = {key: i for i, key in enumerate([
        'none', 'mtobject', 'string', 'float', 'int', 'point', 'multipoint',
        'polygon', 'multipolygon', 'line', 'multiline'])}

    __tablename__ = 'property'

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[Optional[int]]
    name_a: Mapped[str] = mapped_column(index=True)
    name_b: Mapped[Optional[str]] = mapped_column(index=True)

    item_id: Mapped[int] = mapped_column(ForeignKey('mtobject.id', ondelete="CASCADE"),
                                         index=True)
    item: Mapped[MTObject] = relationship(back_populates="properties",
                                          foreign_keys=item_id)

    value_mtobject_id: Mapped[Optional[int]] = mapped_column(
            ForeignKey('mtobject.id', ondelete="CASCADE"),
            index=True
            )
    value_mtobject: Mapped[Optional[MTObject]] = relationship(back_populates="property_values",
                                                              foreign_keys=value_mtobject_id)

    value_literal: Mapped[Optional[str]] = mapped_column(index=True)
    value_geo: Mapped[Optional[Geometry]] = mapped_column(Geometry)

    sourceref: Mapped[str] = mapped_column(index=True)

    # datalinker_id = Column(Integer, ForeignKey('datalinker.id'))
    # datalinker = relationship("DataLinker", back_populates="attributes")

    date_start: Mapped[Optional[date]]
    date_end: Mapped[Optional[date]]
    date_point: Mapped[Optional[date]]

    # overwrite_id = Column(Integer, ForeignKey('property.id'))
    # overwrite = relationship("Property", remote_side=[id])
    # overwrittenby = relationship("Property", back_populates="overwrite")

    context: Mapped[JSON] = mapped_column(JSON)
    timestamp: Mapped[datetime]

    def __init__(self,
                 name: str,
                 value: (str | int | float | MTObject | Polygon | MultiPolygon |
                         LineString | MultiLineString | Point | MultiPoint |
                         numpy.number),
                 sourceref: str,
                 date_point: str | date | None = None,
                 date_start: str | date | None = None,
                 date_end: str | date | None = None,
                 context: int = 0):
        """Constructeur de la propriété.

        Parameters:
            name: Nome complet de la propriété.
            value: Valeur de la propriété.
            mtobject: L'objet lié à la propriété.
            sourceref: La source de référence de la propriété.
            date_point: La date ponctuelle de la propriété.
            date_start: La date de début de la propriété.
            date_end: La date de fin de la propriété.
            context: ???

        Raises:
            ValueError: Quand la valeur est vide.
            TypeError: Quand le type de la valeur est incorrect.
        """
        if value is None or value == '':
            raise ValueError(f"Cannot set a property with an empty value ({value=}).")

        name_a, *name_b = name.split('@', 1)
        self.name_a = name_a
        if name_b:
            self.name_b = name_b[0]

        value_type = get_classname(value)
        self.type = Property.dictoftypes[value_type]
        # modification de la variable adaptée
        if value_type == "mtobject":
            self.value_mtobject_id = value.id
        elif value_type == "string":
            self.value_literal = value
        elif value_type == "float" or value_type == "int":
            self.value_literal = str(value)
        elif value_type == 'point' or value_type == 'multipoint' or \
                value_type == 'polygon' or value_type == 'multipolygon' or \
                value_type == 'line' or value_type == 'multiline':
            self.value_geo = from_shape(value)
        else:
            raise TypeError(f"Invalid Property type {type(value)=}")

        self.sourceref = sourceref
        self.date_start = to_date(date_start)
        self.date_end = to_date(date_end)
        self.date_point = to_date(date_point)
        self.timestamp = datetime.now()
        self.context = context

    @reconstructor
    def init_on_load(self) -> None:
        """Charge la propriété dans le cache de l'objet auquel elle appartient."""
        fullname = self.name_a
        if self.name_b is not None:
            fullname += "@" + self.name_b
        if fullname not in self.item.cached_properties:
            self.item.cached_properties[fullname] = []
        self.item.cached_properties[fullname].append(self)

    def get_value(self) -> (str | int | float | MTObject | Polygon | MultiPolygon |
                            LineString | MultiLineString | Point | MultiPoint):
        """Renvoie la valeur de la propriété."""
        value_type = list(Property.dictoftypes.keys())[self.type]

        if value_type == "mtobject":
            return self.value_mtobject
        elif value_type == "string":
            return self.value_literal
        elif value_type == "float":
            return float(self.value_literal)
        elif value_type == "int":
            return int(self.value_literal)
        elif value_type == 'point' or value_type == 'multipoint' or \
                value_type == 'polygon' or value_type == 'multipolygon' or \
                value_type == 'line' or value_type == 'multiline':
            return to_shape(self.value_geo)
        else:
            raise TypeError("Property type error = '" + str(self.type) + "'")

    @staticmethod
    def tabname(property_name: str) -> list[str | None]:
        """Divise le un nom de propriété en deux."""
        if len(property_name) == 2:
            print(f"Calling tabname with already two parts : {property_name=}")
            return property_name
        return property_name.split('@') if '@' in property_name else [property_name, None]

    def get_name(self) -> str:
        """Renvoie le nom complet de la propriété."""
        return self.name_a + ('' if self.name_b is None else f'@{self.name_b}')

    def get_type(self) -> str:
        """Renvoie le type de la valeur de la propriété."""
        return list(Property.dictoftypes.keys())[self.type]

    def get_value_str(self) -> str:
        """Renvoie la valeur de la propriété sous forme de string."""
        if self.type == Property.dictoftypes["mtobject"]:
            return str(self.value_mtobject)
        elif self.type == Property.dictoftypes["string"] or \
                self.type == Property.dictoftypes["float"] \
                or self.type == Property.dictoftypes["int"]:
            return str(self.value_literal)
        return f"<Object type {self.type}>"

    def get_datetime_str(self) -> str:
        """Renvoie la temporalité de la propriété sous forme de string."""
        _return_str = ""
        if self.date_point is not None:
            _return_str += " [" + str(self.date_point) + "]"
        if self.date_start is not None or self.date_end:
            _return_str += " [" + str(self.date_start) + \
                          "->" + str(self.date_end) + "]"
        return _return_str

    def get_sourceref_str(self) -> str:
        """Renvoie la source de référence de la propriété."""
        return self.sourceref

    def __str__(self) -> str:
        return (f'{self.get_name()} ({self.get_type()}) - {self.get_value_str()}'
                f' - {self.get_datetime_str()} - {self.get_sourceref_str()}')

    def __repr__(self) -> str:
        return f"<Property:{self.name_a}>"

    def has_date(self) -> bool:
        """Détermine si la propriété est liée à une temporalité."""
        return (self.date_point is not None
                or self.date_start is not None
                or self.date_end is not None)


def get_classname(value: (str | int | float | MTObject | Polygon | MultiPolygon |
                          LineString | MultiLineString | Point | MultiPoint |
                          numpy.number)
                  ) -> str:
    from .mtobject import MTObject

    if isinstance(value, numpy.number):
        value = value.item()

    match value:
        case str():
            return 'string'
        case int():
            return 'int'
        case float():
            return 'float'
        case Polygon():
            return 'polygon'
        case MultiPolygon():
            return 'multipolygon'
        case LineString():
            return 'line'
        case MultiLineString():
            return 'multiline'
        case Point():
            return 'point'
        case MultiPoint():
            return 'multipoint'
        case MTObject():
            return 'mtobject'
        case _:
            return 'unknown'
