from __future__ import annotations

from typing import Literal

from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy import PickleType
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from sinamet.tools.unitconverter import convert, get_unit_coeff, ConversionError

from .mtobject import MTObject
from .product import Product


class MTQuantifiable(MTObject):
    """
    Classe mère des objets quantifiables du modèle de Sinamet : `Gateflow`, `Pathflow`, `Stock`

    Parameters:
        properties: Liste des propriétés de l'objet
        type: type d'objet (parmis `gateflow`, `pathflow`, `stock`)
        product: Produit associé à l'élément quantifiable
        quantity: Dictionnaire de la quantité dans différentes unités
        date_start : Repère temporel (Début) de l'élément quantifiable
        date_end: Repère temporel (Fin) de l'élément quantifiable
        date_point: Repère temporel (Date ponctuelle) de l'élément quantifiable
    """
    __tablename__ = 'mtquantifiable'
    __mapper_args__ = {
        'polymorphic_identity': __tablename__
    }

    id: Mapped[int] = mapped_column(ForeignKey('mtobject.id', ondelete='CASCADE'),
                                    primary_key=True)

    product_id: Mapped[int | None] = mapped_column(ForeignKey('product.id'))
    product: Mapped[Product | None] = relationship(foreign_keys=product_id)

    date_point: Mapped[date | None]

    quantity: Mapped[PickleType] = mapped_column(PickleType)

    def __init__(self):
        MTObject.__init__(self)
        self.quantity = {}

    def __str__(self) -> str:
        quantity = next((f'{val} {key}' for key, val in self.quantity.items()), None)

        if self.date_point is not None:
            date = f'[{self.date_point}]'
        else:
            date = f'[{self.date_start} -> {self.date_end}]'

        if (name := self.get_name()) is not None:
            name = f'Name: {name}'
        if (code := self.get_code()) is not None:
            code = f'Code: {code}'
        product_name = str(self.product.get_name()) if self.product else ''

        return f'<{" | ".join(filter(None, (
            f'{self.__class__.__name__}-{self.id}',
            name, code, product_name, date, quantity
        )))}>'

    def get_quantity(self, unit: str,
                     error: Literal['raise', 'none', 'print'] = 'raise',
                     ) -> float | None:
        """Retourne une quantité.

        Parameters:
            unit: Unité de la quantité (euro, kg, ...).
            error: Comportement à adopter en cas d'erreur.

        Note: FutureDev
            Remasteriser cette fonction.
        """
        try:
            product = self.product
            if product is None:
                raise AttributeError("None product associated to : %s" % repr(self))

            quant = self.quantity
            # CAS 1 : Unité déjà présente dans quant : on retourne
            if unit in quant:
                return quant[unit]

            # CAS 2 : Unité déjà présente dans quant avec un prefixe différent ou
            # une équivalence prédéterminée
            for key, val in quant.items():
                try:
                    return convert(val, key, unit)
                except ConversionError:
                    pass

            # CAS 3 : Unité non directement convertible, on utilise les coefficients
            # Associés au produit
            # Construction du dictionnaire
            lst_coeff_attr = product.get_properties("Coefficient",
                                                    return_type="property")
            if not lst_coeff_attr:
                raise ConversionError(f'Unable to convert: no coefficients found in {product=}'
                                      f' ({quant=})')

            # Extracting information
            if type(lst_coeff_attr) is not list:
                lst_coeff_attr = [lst_coeff_attr]

            _conversiondict = {}
            for coeff_attr in lst_coeff_attr:
                _coeff = coeff_attr.name_b
                # _conversiondict[_coeff] = coeff_attr.get_value() TODO: à vérifier

                (_unit1, _unit2) = _coeff.split("/")
                # Correction des coefficients (parce qu'on peut avoir kWh / Euros)
                (standard_unit1, coeff_unit1) = get_unit_coeff(_unit1)
                (standard_unit2, coeff_unit2) = get_unit_coeff(_unit2)
                _conversiondict[standard_unit1 + "/" + standard_unit2] = (coeff_attr.get_value()
                                                                          * float(coeff_unit1)/coeff_unit2)
            for key, val in quant.items():
                try:
                    return convert(val, key, unit, _conversiondict)
                except ConversionError:
                    pass
            # CAS 4 : ???
            raise ConversionError("Unable to express : %s in %s. Available coefficients = %s" % (self.quantity, unit, _conversiondict))

        except ConversionError as e:
            if error == "none":
                return None
            print("ERROR WITH = %s" % repr(self))
            if error == "print":
                print(e)
                return None
            raise e

    def copy(self) -> MTQuantifiable:
        """Deep copy d'un objet quantifiable.

        Note: FutureDev
            Vérifier usage.
        """
        mtq = self.__class__()
        mtq.product = self.product
        mtq.quantity = self.quantity.copy()
        return mtq
