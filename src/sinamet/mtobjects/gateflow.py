from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .quantifiable import MTQuantifiable
from .actor import Actor
from .territory import Territory


class Gateflow(MTQuantifiable):
    """Table flux de porte."""
    __tablename__ = 'gateflow'
    id: Mapped[int] = mapped_column(ForeignKey('mtquantifiable.id', ondelete='CASCADE'),
                                    primary_key=True)

    actor_id: Mapped[int | None] = mapped_column(ForeignKey('actor.id'))
    actor: Mapped[Actor | None] = relationship(foreign_keys=actor_id)

    territory_id: Mapped[int | None] = mapped_column(ForeignKey('territory.id'))
    territory: Mapped[Territory | None] = relationship(foreign_keys=territory_id)

    flowtype: Mapped[str] = mapped_column(String(50))

    __mapper_args__ = {
        'polymorphic_identity': __tablename__,
    }
