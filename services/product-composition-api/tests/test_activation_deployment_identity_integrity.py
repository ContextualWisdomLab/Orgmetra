import pytest

from orgmetra_product_composition import ActivationRegistryError, DeploymentIdentity
from orgmetra_product_composition.activation import PostgresActivationRegistry


def test_valid_to_valid_deployment_retarget_fails_before_database_access() -> None:
    deployment = DeploymentIdentity("orgmetra_gateway", "production")
    object.__setattr__(deployment, "environment_id", "staging")

    registry = PostgresActivationRegistry(lambda: None)  # database must remain untouched
    with pytest.raises(ActivationRegistryError, match="construction snapshot"):
        registry.recover_active(deployment)
