"""Regression for runtime-type integrity of disposition request evidence."""

import pytest

from orgmetra_hr_data_disposition import HrDataDispositionExecutionRequest


def test_disposition_request_cannot_be_subclassed_to_forge_execution_authority() -> None:
    """A caller cannot override non-authorizing properties through a request subclass."""
    with pytest.raises(TypeError, match="final"):

        class ForgedDispositionRequest(HrDataDispositionExecutionRequest):
            """Attempt to turn a request into forged execution authority."""

            @property
            def execution_authorization_state(self) -> str:
                """Forge a destructive state if subclassing were permitted."""
                return "authorized_to_execute"
