"""Bitemporal value objects and deterministic historical fact resolution."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Protocol, TypeVar

from .errors import InvalidDomainValueError, TemporalAmbiguityError


def _require_aware(value: datetime, field_name: str) -> None:
    """Require an explicit UTC offset so system-time comparisons are reliable."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidDomainValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class BitemporalPeriod:
    """Represent half-open effective and recorded intervals for one fact.

    ``effective_*`` describes when the fact is valid in the real world.
    ``recorded_*`` describes when Orgmetra knew the fact. A missing end means
    the corresponding interval remains open.
    """

    effective_from: date
    effective_to: date | None
    recorded_from: datetime
    recorded_to: datetime | None

    def __post_init__(self) -> None:
        """Reject reversed intervals and ambiguous system timestamps."""

        _require_aware(self.recorded_from, "recorded_from")
        if self.recorded_to is not None:
            _require_aware(self.recorded_to, "recorded_to")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise InvalidDomainValueError("effective_to must be later than effective_from")
        if self.recorded_to is not None and self.recorded_to <= self.recorded_from:
            raise InvalidDomainValueError("recorded_to must be later than recorded_from")

    def is_effective_on(self, day: date) -> bool:
        """Return whether the fact is effective on ``day`` using half-open bounds."""

        return self.effective_from <= day and (
            self.effective_to is None or day < self.effective_to
        )

    def was_known_at(self, moment: datetime) -> bool:
        """Return whether the fact was visible to Orgmetra at ``moment``."""

        _require_aware(moment, "moment")
        return self.recorded_from <= moment and (
            self.recorded_to is None or moment < self.recorded_to
        )


class _BitemporalFact(Protocol):
    """Structural type for domain facts that expose one bitemporal period."""

    period: BitemporalPeriod


_BitemporalFactT = TypeVar("_BitemporalFactT", bound=_BitemporalFact)


def resolve_bitemporal_fact(
    facts: Iterable[_BitemporalFactT],
    *,
    effective_on: date,
    known_at: datetime,
) -> _BitemporalFactT | None:
    """Return the sole fact visible at one business-time/knowledge-time coordinate.

    A missing match returns ``None``. More than one visible fact is a data-integrity
    violation, so the resolver fails closed instead of selecting by collection order.
    The knowledge-time coordinate must carry an explicit UTC offset.
    """

    _require_aware(known_at, "known_at")
    visible_facts = [
        fact
        for fact in facts
        if fact.period.is_effective_on(effective_on) and fact.period.was_known_at(known_at)
    ]
    if not visible_facts:
        return None
    if len(visible_facts) > 1:
        raise TemporalAmbiguityError(
            "multiple facts are visible at the requested bitemporal coordinate"
        )
    return visible_facts[0]
