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
        _str_return = "<Territory-" + str(self.id) + ": " \
                    + str(self.get_code()) + "-" + str(self.get_name(force_cache=False, raise_none=False)) + ">"
        return _str_return
