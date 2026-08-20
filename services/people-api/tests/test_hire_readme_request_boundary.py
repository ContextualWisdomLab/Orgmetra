"""Documentation regression for the confirmed-hire HTTP trust boundary."""

from pathlib import Path
import unittest


_PEOPLE_API_README = Path(__file__).resolve().parents[1] / "README.md"


class HireReadmeRequestBoundaryTests(unittest.TestCase):
    """Keep buyer-facing confirmed-hire transport guarantees code-current."""

    def test_confirmed_hire_documents_pre_body_authentication_and_limits(self) -> None:
        readme = _PEOPLE_API_README.read_text(encoding="utf-8")

        self.assertIn("authentication and tenant binding occur before request-body parsing", readme)
        self.assertIn("64 KiB cumulative request-body limit", readme)
        self.assertIn("1024 ASGI request frames", readme)
        self.assertIn("Idempotency-Key", readme)
        self.assertIn("one tenant-bound transaction", readme)


if __name__ == "__main__":
    unittest.main()
