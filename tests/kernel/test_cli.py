import json

from eaon_kernel.cli import main


def test_cli_lifecycle_without_migrating_stores(tmp_path, capsys):
    db = tmp_path / "new.db"
    source = tmp_path / "source.txt"
    source.write_text("Synthetic evidence: keep the project local.", encoding="utf-8")
    def run(*args):
        status = main(["--db", str(db), *args])
        output = capsys.readouterr()
        return status, json.loads(output.out or output.err)
    assert run("init")[0] == 0
    assert run("project", "p", "Project")[0] == 0
    assert run("goal", "p", "g", "Confirm evidence")[0] == 0
    assert run("remember", "p", "d", "Stay local", "--status", "confirmed")[0] == 1
    assert run("remember", "p", "d", "Stay local", "--status", "confirmed", "--kind", "evidence", "--source-file", str(source))[0] == 0
    assert run("unknown", "p", "missing", "No microphone measurement")[0] == 0
    assert run("task", "p", "t", "Measure microphone")[0] == 0
    status, card = run("recover", "p")
    assert status == 0 and card["next_task"]["id"] == "t"
    status, context = run("context", "p", "local")
    assert status == 0 and context["evidence"]["authority"] == "candidate_only"
    assert run("revoke", "p", "evidence:d", "Source withdrawn", "--expected-revision", "1")[0] == 0
    assert run("context", "p", "local")[1]["evidence"]["status"] == "unknown"
    assert "evidence:d" not in run("context", "p", "local")[1]["project"]["memories"]


def test_cli_missing_or_corrupt_store_does_not_initialize(tmp_path, capsys):
    path = tmp_path / "missing.db"
    assert main(["--db", str(path), "verify"]) == 1
    assert not path.exists()
    path.write_text("broken")
    assert main(["--db", str(path), "verify"]) == 1
    assert path.read_text() == "broken"
