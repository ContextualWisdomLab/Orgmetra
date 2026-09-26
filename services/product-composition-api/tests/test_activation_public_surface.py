from __future__ import annotations

import orgmetra_product_composition as product_composition


def test_structural_activation_registry_is_not_a_product_public_entrypoint() -> None:
    assert "AuthorizedPostgresActivationRegistry" in product_composition.__all__
    assert "PostgresActivationRegistry" not in product_composition.__all__
    assert not hasattr(product_composition, "PostgresActivationRegistry")


def test_unbound_route_availability_projection_is_not_a_product_public_entrypoint() -> None:
    assert "available_route_ids_for" not in product_composition.__all__
    assert not hasattr(product_composition, "available_route_ids_for")


def test_recovery_bound_route_snapshot_is_the_supported_route_projection_surface() -> None:
    assert "RecoveredRouteSnapshot" in product_composition.__all__
    assert "recover_active_route_snapshot" in product_composition.__all__
    assert "current_route_ids_for_snapshot" in product_composition.__all__
    assert hasattr(product_composition, "RecoveredRouteSnapshot")
    assert hasattr(product_composition, "recover_active_route_snapshot")
    assert hasattr(product_composition, "current_route_ids_for_snapshot")
