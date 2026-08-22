"""Regression for runtime-type integrity of disposition request evidence."""

import pytest

from orgmetra_hr_data_disposition import HrDataDispositionExecutionRequest


def _forged_execution_authority(_request: object) -> str:
    """Return the destructive value an attacker would try to inject via inheritance."""
    return "authorized_to_execute"


def test_disposition_request_cannot_be_subclassed_to_forge_execution_authority() -> None:
    """A caller cannot override non-authorizing properties through a request subclass."""
    with pytest.raises(TypeError, match="final"):
        type(
            "ForgedDispositionRequest",
            (HrDataDispositionExecutionRequest,),
            {"execution_authorization_state": property(_forged_execution_authority)},
        )
