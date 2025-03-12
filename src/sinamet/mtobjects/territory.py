from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .mtobject import MTObject


class Territory(MTObject):
    """Table territoire."""
    __tablename__ = 'territory'

    id: Mapped[int] = mapped_column(ForeignKey('mtobject.id', ondelete='CASCADE'),
                                    primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': __tablename__,
    }

    def __str__(self) -> str:
        return f'<Territory-{self.id}: {self.get_code()}-{self.get_name()}>'
