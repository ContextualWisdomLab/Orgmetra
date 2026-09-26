from __future__ import annotations

import pytest

from orgmetra_product_composition import (
    CompositionMethodNotImplementedError,
    CompositionRequestError,
    current_route_id_for_request,
)


@pytest.mark.parametrize("method", ["M-SEARCH", "X1", "get", "A_B", "THIS-METHOD-NAME-IS-LONGER"])
def test_valid_http_tokens_outside_server_profile_fail_as_not_implemented_before_state_use(
    method: str,
) -> None:
    with pytest.raises(CompositionMethodNotImplementedError):
        current_route_id_for_request(
            object(),
            object(),
            object(),
            method=method,
            request_path="/v1/people/current",
        )


@pytest.mark.parametrize("method", ["", "GET POST", "GET\nPOST", "GET/POST"])
def test_non_token_methods_remain_invalid_requests(method: str) -> None:
    with pytest.raises(CompositionRequestError):
        current_route_id_for_request(
            object(),
            object(),
            object(),
            method=method,
            request_path="/v1/people/current",
        )
