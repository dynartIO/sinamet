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

    def __str__(self):
        temp_emitter_actor = "A?" if self.emitter_actor is None else self.emitter_actor.get_name()
        temp_emitter_territory = "T?" if self.emitter_territory is None else self.emitter_territory.get_code()
        temp_receiver_actor = "A?" if self.receiver_actor is None else self.receiver_actor.get_name()
        temp_receiver_territory = "T?" if self.receiver_territory is None else self.receiver_territory.get_code()
        temp_omes = " !! NO PRODUCT !! " if self.product is None else "[" + self.product.get_code().ljust(5) + "] " \
            + self.product.get_name()

        for key, val in self.quantity.items():
            qunit = "%s %s" % (val, key)
            break

        return "<Pathflow " + temp_omes.ljust(50)[:50] + " "\
               + str(qunit) + " [%s @ %s] -> [%s @ %s]>" % \
               (temp_emitter_territory, temp_emitter_actor,
                temp_receiver_territory, temp_receiver_actor)
