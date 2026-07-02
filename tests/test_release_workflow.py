import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_push_builds_only_when_version_file_changes(self):
        self.assertRegex(self.workflow, r"(?m)^  push:\n(?:    .+\n)*    paths:\n      - version\.py$")

    def test_release_tag_is_based_on_app_version_not_run_number(self):
        tag_assignment = re.search(r'RELEASE_TAG="([^"]+)"', self.workflow)

        self.assertIsNotNone(tag_assignment)
        self.assertEqual(tag_assignment.group(1), "v${APP_VERSION}")


if __name__ == "__main__":
    unittest.main()
