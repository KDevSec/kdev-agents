from pathlib import Path
from kdev_cluster_x3.lib.standards_lint import lint_standards_dir

ROOT = Path(__file__).parent.parent


def test_no_lint_issues_after_full_population():
    issues = lint_standards_dir(ROOT / "standards")
    assert issues == [], f"standards lint failed: {issues}"
