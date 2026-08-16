"""Static contracts for explicit authority and non-leaking API behavior."""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "orgmetra_people_api"


def _source_text() -> str:
    """Return all shipped people API source as one audit string."""

    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(PACKAGE_ROOT.glob("*.py"))
    )


def test_api_has_no_ambient_environment_or_static_token_authority() -> None:
    source = _source_text()

    forbidden_terms = {
        "os.environ",
        "os.getenv",
        "STATIC_TOKEN",
        "X-Tenant-Id",
        "X-Orgmetra-Tenant",
        "allow_origins=[\"*\"]",
        "secrets: inherit",
    }
    for term in forbidden_terms:
        assert term not in source
    assert "TokenAuthorizer" in source
    assert "PurposeContext" in source


def test_problem_responses_do_not_include_sensitive_exception_fields() -> None:
    source = (PACKAGE_ROOT / "problems.py").read_text(encoding="utf-8")

    forbidden_problem_fields = {
        '"exception"',
        '"stack_trace"',
        '"sql"',
        '"database_url"',
        '"display_name"',
        '"assessment_response"',
        '"compensation_amount"',
        "trace_reference",
        "x-request-id",
    }
    for field_name in forbidden_problem_fields:
        assert field_name not in source.casefold()
    assert "application/problem+json" in source
    assert "support_reference" in source
    assert "next_action" in source


def test_route_scopes_and_purposes_are_server_selected_constants() -> None:
    source = (PACKAGE_ROOT / "app.py").read_text(encoding="utf-8")

    assert 'RequiredPurpose("orgmetra.people.write", "people_admin")' in source
    assert 'RequiredPurpose("orgmetra.people.read", "people_read")' in source
    assert '"orgmetra.talent_acquisition.write",\n        "talent_acquisition"' in source
    assert 'RequiredPurpose("orgmetra.audit.read", "audit_review")' in source
    assert "X-Purpose" not in source
    assert "X-Decision-Reference" not in source
    assert "X-Evidence-Reference" not in source


def test_route_dependencies_stay_server_owned_at_runtime() -> None:
    source = (PACKAGE_ROOT / "app.py").read_text(encoding="utf-8")

    assert "from __future__ import annotations" not in source
    assert "context: PurposeContext = Depends(" in source
    assert "repository_port: PeopleRepository = Depends(get_people_repository)" in source
    assert "Annotated[PurposeContext" not in source
    assert "request.app.state.repository" not in source.split("async def create_person", 1)[1]


def test_person_command_cannot_accept_system_recorded_time() -> None:
    app_source = (PACKAGE_ROOT / "app.py").read_text(encoding="utf-8")
    schema_source = (PACKAGE_ROOT / "schemas.py").read_text(encoding="utf-8")
    repository_source = (PACKAGE_ROOT / "repository.py").read_text(encoding="utf-8")

    assert "payload.recorded_at" not in app_source
    person_schema = schema_source.split("class PersonCreateRequest", 1)[1].split(
        "class PersonResponse", 1
    )[0]
    person_port = repository_source.split("def create_person", 1)[1].split(
        "def get_person", 1
    )[0]
    assert "recorded_at" not in person_schema
    assert "recorded_at" not in person_port
