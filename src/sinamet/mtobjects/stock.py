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

    def __str__(self) -> str:
        _strquantity = ""
        for key, val in self.quantity.items():
            _strquantity += str(val) + " " + key + " / "
        actor_terr = ""
        if self.territory is not None:
            actor_terr += "Territory : %s" % self.territory
        if self.territory is not None and self.actor is not None:
            actor_terr += " & "
        if self.actor is not None:
            actor_terr += "Actor : %s" % self.actor
        if actor_terr == "":
            actor_terr = "!NO LINK!"

        return "<Stock-%s:%s | %s | %s | %s | %s | %s>" % \
            (self.id, self.product.get_name(),
             "self.str_period()", _strquantity,
             actor_terr, self.get_code(raise_none=False),
             self.get_name(raise_none=False))
