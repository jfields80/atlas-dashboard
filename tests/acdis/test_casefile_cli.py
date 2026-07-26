import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def test_cli_writes_report_and_refuses_existing_output_without_overwrite(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    temp_dir = Path(tempfile.mkdtemp(prefix="acdis-cli-", dir=str(repo_root)))
    try:
        input_path = temp_dir / "case.json"
        output_path = temp_dir / "report.md"
        input_path.write_text(json.dumps({
            "case_id": "case-004",
            "case_title": "CLI case",
            "opportunity_name": "CLI opportunity",
            "target_market": "CLI market",
            "proposed_directory_category": "CLI category",
            "customer_type": "CLI customers",
            "user_problem": "CLI problem",
            "proposed_minimum_useful_pilot": "CLI pilot",
            "likely_monetization_paths": ["Lead referrals"],
            "potential_data_moat_opportunities": ["Local data"],
            "reasons_not_to_pursue": ["No funding"],
            "next_research_actions": ["Talk to operators"],
            "competitors": [{"competitor_id": "comp-1", "name": "Example Co"}],
            "evidence": [{
                "evidence_id": "evidence-1",
                "evidence_type": "FACT",
                "statement": "Observed signal",
                "source_references": ["Manual interview"],
            }],
        }), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "acdis", "render-case", str(input_path), "--output", str(output_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert output_path.exists()

        second_result = subprocess.run(
            [sys.executable, "-m", "acdis", "render-case", str(input_path), "--output", str(output_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert second_result.returncode != 0
        assert "overwrite" in second_result.stderr.lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
