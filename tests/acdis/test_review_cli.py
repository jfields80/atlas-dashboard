import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from review_fixtures import make_review_case_data


def test_review_case_cli_writes_and_overwrite_behavior():
    repo_root = Path(__file__).resolve().parents[2]
    temp_dir = Path(tempfile.mkdtemp(prefix="acdis-review-cli-", dir=str(repo_root)))
    try:
        input_path = temp_dir / "review_case.json"
        output_path = temp_dir / "review_report.md"
        input_path.write_text(json.dumps(make_review_case_data()), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "acdis", "review-case", str(input_path), "--output", str(output_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert output_path.exists()

        second = subprocess.run(
            [sys.executable, "-m", "acdis", "review-case", str(input_path), "--output", str(output_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert second.returncode != 0
        assert "overwrite" in second.stderr.lower()

        overwrite = subprocess.run(
            [
                sys.executable,
                "-m",
                "acdis",
                "review-case",
                str(input_path),
                "--output",
                str(output_path),
                "--overwrite",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert overwrite.returncode == 0, overwrite.stderr
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_review_case_cli_rejects_unsafe_path():
    repo_root = Path(__file__).resolve().parents[2]
    temp_dir = Path(tempfile.mkdtemp(prefix="acdis-review-cli-", dir=str(repo_root)))
    try:
        input_path = temp_dir / "review_case.json"
        input_path.write_text(json.dumps(make_review_case_data()), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "acdis", "review-case", str(input_path), "--output", r"C:\\Atlas\\unsafe.md"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "rejected" in result.stderr.lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_review_case_cli_invalid_input_returns_nonzero(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    input_path = tmp_path / "bad.json"
    output_path = tmp_path / "out.md"
    input_path.write_text("{not-json", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "acdis", "review-case", str(input_path), "--output", str(output_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_render_case_command_still_operational(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    temp_dir = Path(tempfile.mkdtemp(prefix="acdis-render-cli-", dir=str(repo_root)))
    try:
        input_path = temp_dir / "phase1.json"
        output_path = temp_dir / "phase1.md"
        data = make_review_case_data()
        data.pop("review")
        input_path.write_text(json.dumps(data), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "acdis", "render-case", str(input_path), "--output", str(output_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert output_path.exists()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
