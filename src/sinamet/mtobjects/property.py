from __future__ import annotations
from datetime import date, datetime
import enum
from typing import Any, TYPE_CHECKING

from geoalchemy2 import Geometry, WKBElement
from geoalchemy2.shape import from_shape, to_shape
import shapely
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import reconstructor

from sinamet.tools.timext import to_date

from .dbobject import DBObjectClassBase

if TYPE_CHECKING:
    from .mtobject import MTObject


class Property(DBObjectClassBase):
    """Objet Property

     Attributes:
            item: L'objet lié à la propriété.
            source_ref: La source de référence de la propriété.
            date_point: La date ponctuelle de la propriété (si existante).
            date_start: La date de début de la propriété (si existante).
            date_end: La date de fin de la propriété (si existante).
            value_mtobject: La valeur de la propriété si c'est une relation avec un autre MTObject.
            value_literal: La valeur si c'est un nombre ou du texte.
            value_geo: La valeur si c'est une forme géographique.
            context: Dictionnaire complémentaire pour contextualiser la propriété (Optionnel)
            timestamp: Date d'insertion de la propriété dans la base de données.
    """
    class ValueType(enum.Enum):
        MTOBJECT = 1
        STRING = 2
        FLOATING = 3
        INTEGER = 4
        GEOMETRY = 5

    __tablename__ = 'property'

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[ValueType] = mapped_column(Enum(ValueType))
    name_a: Mapped[str] = mapped_column(index=True)
    name_b: Mapped[str | None] = mapped_column(index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey('mtobject.id',
                                                    ondelete="CASCADE"),
                                         index=True)
    item: Mapped[MTObject] = relationship(back_populates="properties",
                                          foreign_keys=item_id)
    value_mtobject_id: Mapped[int | None] = mapped_column(
            ForeignKey('mtobject.id', ondelete="CASCADE"),
            index=True)
    value_mtobject: Mapped[MTObject | None] = relationship(
            back_populates="property_values",
            foreign_keys=value_mtobject_id)
    value_literal: Mapped[str | None] = mapped_column(index=True)
    value_geo: Mapped[WKBElement | None] = mapped_column(Geometry)
    source_ref: Mapped[str | None] = mapped_column(index=True)
    date_start: Mapped[date | None]
    date_end: Mapped[date | None]
    date_point: Mapped[date | None]
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    timestamp: Mapped[datetime]

    # datalinker_id = Column(Integer, ForeignKey('datalinker.id'))
    # datalinker = relationship("DataLinker", back_populates="attributes")
    # overwrite_id = Column(Integer, ForeignKey('property.id'))
    # overwrite = relationship("Property", remote_side=[id])
    # overwrittenby = relationship("Property", back_populates="overwrite")

    def __init__(self,
                 name: str,
                 value: str | int | float | MTObject | shapely.Geometry,
                 source_ref: str | None = None,
                 date_point: str | date | None = None,
                 date_start: str | date | None = None,
                 date_end: str | date | None = None,
                 context: dict[str, Any] | None = None) -> None:
        """Constructeur de la propriété.

        Parameters:
            name: Nome complet de la propriété.
            value: Valeur de la propriété.
            source_ref: La source de référence de la propriété.
            date_point: La date ponctuelle de la propriété.
            date_start: La date de début de la propriété.
            date_end: La date de fin de la propriété.
            context: Dictionnaire complémentaire pour contextualiser la propriété (Optionnel)

        Raises:
            ValueError: Quand la valeur est vide.
            TypeError: Quand le type de la valeur est incorrect.
        """
        from .mtobject import MTObject

        if value is None or value == '':
            raise ValueError(f'Cannot set a property with an empty value ({value=}).')

        name_a, *name_b = name.split('@', 1)
        self.name_a = name_a
        if name_b:
            self.name_b = name_b[0]

        match value:
            case MTObject():
                self.value_mtobject = value
                self.type = self.ValueType.MTOBJECT
            case str():
                self.value_literal = value
                self.type = self.ValueType.STRING
            case int():
                self.value_literal = str(value)
                self.type = self.ValueType.INTEGER
            case float():
                self.value_literal = str(value)
                self.type = self.ValueType.FLOATING
            case shapely.Geometry():
                self.value_geo = from_shape(value)
                self.type = self.ValueType.GEOMETRY
            case _:
                raise TypeError(f'Invalid Property type ({type(value)})')

        self.source_ref = source_ref
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

    def get_value(self) -> (str | int | float | MTObject | shapely.Geometry):
        """Renvoie la valeur de la propriété.
        Peut être un litéral (texte, nombre), un MTObject ou une forme géographique
        """
        if self.type.name == 'MTOBJECT' and self.value_mtobject:
            return self.value_mtobject
        if self.type.name == 'STRING' and self.value_literal:
            return self.value_literal
        if self.type.name == 'FLOATING' and self.value_literal:
            return float(self.value_literal)
        if self.type.name == 'INTEGER' and self.value_literal:
            return int(self.value_literal)
        if self.type.name == 'GEOMETRY' and self.value_geo:
            return to_shape(self.value_geo)
        raise TypeError(f'Invalid Property type ({self.type})')

    def get_name(self) -> str:
        """Renvoie le nom complet de la propriété."""
        return self.name_a + ('' if self.name_b is None else f'@{self.name_b}')

    def get_type(self) -> str:
        """Renvoie le type de la valeur de la propriété."""
        return self.type.name

    def get_value_str(self) -> str:
        """Renvoie la valeur de la propriété sous forme de string."""
        if self.type.name == 'MTOBJECT':
            return str(self.value_mtobject)
        if self.type.name in ('STRING', 'INTEGER', 'FLOATING'):
            return str(self.value_literal)
        return 'Geometry'

    def get_datetime_str(self) -> str:
        """Renvoie la temporalité de la propriété sous forme de string."""
        _return_str = ""
        if self.date_point is not None:
            _return_str += " [" + str(self.date_point) + "]"
        if self.date_start is not None or self.date_end:
            _return_str += " [" + str(self.date_start) + \
                          "->" + str(self.date_end) + "]"
        return _return_str

    def get_source_ref_str(self) -> str | None:
        """Renvoie la source de référence de la propriété."""
        return self.source_ref

    def __str__(self) -> str:
        return (f'{self.get_name()} ({self.get_type()}) - {self.get_value_str()}'
                f' - {self.get_datetime_str()} - {self.get_source_ref_str()}')

    def __repr__(self) -> str:
        return f"<Property:{self.name_a}>"

    def has_date(self) -> bool:
        """Détermine si la propriété est liée à une temporalité."""
        return (self.date_point is not None
                or self.date_start is not None
                or self.date_end is not None)
