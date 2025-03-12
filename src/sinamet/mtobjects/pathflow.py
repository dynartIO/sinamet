from sqlalchemy.schema import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from .quantifiable import MTQuantifiable
from .actor import Actor
from .territory import Territory


class Pathflow(MTQuantifiable):
    """Table flux de chemin."""
    __tablename__ = 'pathflow'

    id: Mapped[int] = mapped_column(ForeignKey('mtquantifiable.id', ondelete='CASCADE'),
                                    primary_key=True)

    emitter_actor_id: Mapped[int | None] = mapped_column(ForeignKey('actor.id'))
    emitter_actor: Mapped[Actor | None] = relationship(foreign_keys=emitter_actor_id)

    emitter_territory_id: Mapped[int | None] = mapped_column(ForeignKey('territory.id'))
    emitter_territory: Mapped[Territory | None] = relationship(foreign_keys=emitter_territory_id)

    receiver_actor_id: Mapped[int | None] = mapped_column(ForeignKey('actor.id'))
    receiver_actor: Mapped[Actor | None] = relationship(foreign_keys=receiver_actor_id)

    receiver_territory_id: Mapped[int | None] = mapped_column(ForeignKey('territory.id'))
    receiver_territory: Mapped[Territory | None] = relationship(foreign_keys=receiver_territory_id)

    __mapper_args__ = {
        'polymorphic_identity': 'pathflow',
    }
