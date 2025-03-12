from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .quantifiable import MTQuantifiable
from .actor import Actor
from .territory import Territory


class Stock(MTQuantifiable):
    """Table stock."""
    __tablename__ = 'stock'

    id: Mapped[int] = mapped_column(ForeignKey('mtquantifiable.id', ondelete='CASCADE'),
                                    primary_key=True)

    actor_id: Mapped[int | None] = mapped_column(ForeignKey('actor.id'))
    actor: Mapped[Actor | None] = relationship()

    territory_id: Mapped[int | None] = mapped_column(ForeignKey('territory.id'))
    territory: Mapped[Territory | None] = relationship()

    __mapper_args__ = {
        'polymorphic_identity': __tablename__,
    }
