from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .mtobject import MTObject


class Product(MTObject):
    """Table produit."""
    __tablename__ = 'product'

    id: Mapped[int] = mapped_column(ForeignKey('mtobject.id', ondelete='CASCADE'),
                                    primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': __tablename__,
    }

    def __str__(self) -> str:
        code = self.get_code(raise_none=False) or 'No code'
        name = self.get_name(raise_none=False) or 'No name'
        nomenclature = self.get_property('Nomenclature', raise_none=False) or 'No nomenclature'
        return f"<Product-{self.id}:{nomenclature}({code})-{name}>"

    def str_hard_property(self) -> str:
        return ""
