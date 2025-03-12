from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .mtobject import MTObject
from .territory import Territory


class Actor(MTObject):
    """Table acteur."""
    __tablename__ = 'actor'

    id: Mapped[int] = mapped_column(ForeignKey('mtobject.id', ondelete='CASCADE'),
                                    primary_key=True)

    territory_id: Mapped[int | None] = mapped_column(ForeignKey('territory.id'))
    territory: Mapped[Territory | None] = relationship(foreign_keys=territory_id)

    __mapper_args__ = {
        'polymorphic_identity': __tablename__,
    }

    def __str__(self) -> str:
        return f'<Actor-{self.id}: {self.get_name()}>'
