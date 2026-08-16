"""Bitemporal value objects and deterministic historical fact resolution."""

from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, TypeVar

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

    def covers_effective_interval(self, other: "BitemporalPeriod") -> bool:
        """Return whether this effective interval contains ``other``'s interval.

        Use this before attaching an assignment to an employment. If the
        employment interval does not cover the assignment, correct the dates
        or choose the employment that was in force.
        """

        if self.effective_from > other.effective_from:
            return False
        if self.effective_to is None:
            return True
        if other.effective_to is None:
            return False
        return other.effective_to <= self.effective_to


class _BitemporalFact(Protocol):
    """Structural type for domain facts that expose one bitemporal period."""

    period: BitemporalPeriod


_BitemporalFactT = TypeVar("_BitemporalFactT", bound=_BitemporalFact)


def resolve_bitemporal_facts_by_identity(
    facts: Iterable[_BitemporalFactT],
    *,
    effective_on: date,
    known_at: datetime,
    identity_of: Callable[[_BitemporalFactT], Hashable],
) -> dict[Hashable, _BitemporalFactT]:
    """Return the visible fact for each identity at one bitemporal coordinate.

    Fail closed only when **one** identity has two visible versions. Review
    overlapping versions for that identity and close the superseded recorded
    interval before querying again.
    """

    _require_aware(known_at, "known_at")
    visible_by_identity: dict[Hashable, list[_BitemporalFactT]] = defaultdict(list)
    for fact in facts:
        if fact.period.is_effective_on(effective_on) and fact.period.was_known_at(known_at):
            visible_by_identity[identity_of(fact)].append(fact)

    resolved: dict[Hashable, _BitemporalFactT] = {}
    for identity, visible_facts in visible_by_identity.items():
        if len(visible_facts) > 1:
            raise TemporalAmbiguityError(
                "multiple versions are visible for one identity at the requested "
                "bitemporal coordinate; review overlapping versions and close the "
                "superseded recorded interval"
            )
        resolved[identity] = visible_facts[0]
    return resolved


def resolve_bitemporal_fact(
    facts: Iterable[_BitemporalFactT],
    *,
    effective_on: date,
    known_at: datetime,
    identity_of: Callable[[_BitemporalFactT], Hashable],
) -> _BitemporalFactT | None:
    """Return the sole fact visible for one identity at one coordinate.

    A missing match returns ``None``. Pass ``identity_of`` so two people, jobs,
    or units are never treated as one ambiguous fact. If the collection spans
    more than one identity, use ``resolve_bitemporal_facts_by_identity`` and
    review each identity separately.
    """

    resolved = resolve_bitemporal_facts_by_identity(
        facts,
        effective_on=effective_on,
        known_at=known_at,
        identity_of=identity_of,
    )
    if not resolved:
        return None
    if len(resolved) > 1:
        raise InvalidDomainValueError(
            "resolve_bitemporal_fact requires facts for one identity; "
            "use resolve_bitemporal_facts_by_identity to review each identity"
        )
    return next(iter(resolved.values()))
