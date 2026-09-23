from __future__ import annotations

import orgmetra_product_composition as product_composition


def test_structural_activation_registry_is_not_a_product_public_entrypoint() -> None:
    assert "AuthorizedPostgresActivationRegistry" in product_composition.__all__
    assert "PostgresActivationRegistry" not in product_composition.__all__
    assert not hasattr(product_composition, "PostgresActivationRegistry")


def test_unbound_route_availability_projection_is_not_a_product_public_entrypoint() -> None:
    assert "available_route_ids_for" not in product_composition.__all__
    assert not hasattr(product_composition, "available_route_ids_for")
