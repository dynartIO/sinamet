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

        return "<Gateflow(%s)-%s:%s | %s | %s | %s>" % \
               (self.flowtype, self.id, self.product.get_name(),
                self.str_period(), _strquantity, actor_terr)

    def str_hard_property(self) -> str:
        _str = "    {%s:%s}\n" % ("self.flowtype", self.flowtype)
        _str += "   {%s:%s}\n" % ("self.product", self.product)
        _str += "   {%s:%s}\n" % ("self.quantity", self.quantity)
        _str += "   {%s:%s}\n" % ("self.territory", self.territory)
        _str += "   {%s:%s}\n" % ("self.actor", self.actor)
        _str += "   {%s:(%s,%s,%s)}\n" % ("self.date_start, end, point",
                                          self.date_start, self.date_end, self.date_point)
        return _str

    def str_period(self) -> str:
        _str_time = "[" + str(self.date_start) + " -> " + str(self.date_end) + "]"
        return _str_time
