"""Assignment allocation runtime-integrity regressions."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from orgmetra_hris_kernel import (
    AssignmentPortfolioError,
    PositionSeatError,
    validate_assignment_portfolio,
    validate_position_seat_capacity,
)

from .conftest import ICU_POSITION, JORDAN, JORDAN_EMPLOYMENT, TENANT, utc


class ForgedAllocationRatio(Decimal):
    """Expose an invalid numeric value while spoofing governed range comparisons."""

    def __gt__(self, other: object) -> bool:
        """Pretend the negative allocation is greater than the lower bound."""
        return True

    def __le__(self, other: object) -> bool:
        """Pretend the negative allocation is no greater than the upper bound."""
        return True


def test_portfolio_rejects_decimal_subclass_before_ratio_comparisons(
    jordan_icu_assignment,
) -> None:
    """Caller-controlled Decimal behavior must not decide an Employment allocation invariant."""
    forged = replace(
        jordan_icu_assignment,
        allocation_ratio=ForgedAllocationRatio("-0.5000"),
    )

    with pytest.raises(AssignmentPortfolioError, match="allocation_ratio"):
        validate_assignment_portfolio(
            [forged],
            tenant_record_id=TENANT,
            person_record_id=JORDAN,
            employment_record_id=JORDAN_EMPLOYMENT,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 5, 1),
        )


def test_position_capacity_rejects_decimal_subclass_before_aggregation(
    jordan_icu_assignment,
) -> None:
    """Caller-controlled Decimal behavior must not decide a Position capacity invariant."""
    forged = replace(
        jordan_icu_assignment,
        allocation_ratio=ForgedAllocationRatio("-0.5000"),
    )

    with pytest.raises(PositionSeatError, match="allocation_ratio"):
        validate_position_seat_capacity(
            [forged],
            tenant_record_id=TENANT,
            position_record_id=ICU_POSITION,
            effective_on=date(2024, 5, 1),
            known_at=utc(2024, 5, 1),
        )
