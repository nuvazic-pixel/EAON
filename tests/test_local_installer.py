"""Installation boundaries tested with temporary folders and fake processes only."""
from io import BytesIO
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts import doctor_local as doctor
from scripts import setup_local as setup


@pytest.fixture
def synthetic_config_io(tmp_path, monkeypatch):
    # The offline guard continues to reject every real dotenv file. Only this
    # test's synthetic .env is backed by a harmless .env.example fixture.
    original = Path.open
    requested = (tmp_path / ".env").absolute()
    def fixture_open(path, *args, **kwargs):
        target = tmp_path / ".env.example" if path.absolute() == requested else path
        return original(target, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fixture_open)


def fixture_environment(root):
    executable = setup.environment_python(root)
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"synthetic interpreter placeholder")
    (root / ".venv/pyvenv.cfg").write_text("home = synthetic\n", encoding="utf-8")
    return executable


def probe_result(root, version=(3, 12), *, prefix=None, base="synthetic-base"):
    return SimpleNamespace(stdout=json.dumps({"version": list(version), "prefix": str(prefix or root / ".venv"), "base": base}), returncode=0)


def test_existing_environment_is_validated_and_reused_without_recreation(tmp_path):
    executable = fixture_environment(tmp_path)
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        return probe_result(tmp_path)
    assert setup.ensure_environment(tmp_path, runner=runner) == executable
    assert len(calls) == 1 and calls[0][:3] == [str(executable), "-I", "-c"]
    assert "venv" not in calls[0]


def test_wrong_existing_python_is_rejected_without_installing_or_deleting(tmp_path):
    executable = fixture_environment(tmp_path)
    with pytest.raises(setup.SetupError, match="^environment_requires_python_312$"):
        setup.ensure_environment(tmp_path, runner=lambda *args, **kwargs: probe_result(tmp_path, (3, 14)))
    assert executable.is_file()


def test_external_prefix_or_nonvenv_is_rejected(tmp_path):
    fixture_environment(tmp_path)
    for info in (probe_result(tmp_path, prefix=tmp_path / "other"), probe_result(tmp_path, base=str(tmp_path / ".venv"))):
        with pytest.raises(setup.SetupError, match="environment_requires_python_312"):
            setup.validate_environment(tmp_path, runner=lambda *args, **kwargs: info)


def test_incomplete_environment_is_preserved(tmp_path):
    target = tmp_path / ".venv"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("keep")
    with pytest.raises(setup.SetupError, match="environment_incomplete"):
        setup.ensure_environment(tmp_path, runner=lambda *args, **kwargs: pytest.fail("must not spawn"))
    assert sentinel.read_text() == "keep"


def test_new_environment_creation_uses_current_explicit_python_without_shell(tmp_path):
    commands = []
    def runner(command, **kwargs):
        commands.append((command, kwargs))
        if command[2:4] == ["-m", "venv"]:
            fixture_environment(tmp_path)
        return probe_result(tmp_path)
    executable = setup.ensure_environment(tmp_path, runner=runner)
    assert commands[0][0] == [setup.sys.executable, "-I", "-m", "venv", str(tmp_path / ".venv")]
    assert executable == setup.environment_python(tmp_path)
    assert all(not kwargs.get("shell", False) for _, kwargs in commands)


def test_existing_config_and_database_are_never_overwritten(tmp_path, synthetic_config_io):
    env = tmp_path / ".env"
    env.write_text("SYNAPSE_TOKEN=private-sentinel\n")
    database = tmp_path / "existing.db"
    database.write_bytes(b"preserved fixture")
    fixture_environment(tmp_path)
    (tmp_path / "requirements-desktop.txt").write_text("streamlit==1.64.0\n")
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        return probe_result(tmp_path)
    result = setup.install(tmp_path, runner=runner)
    assert result["env_file_created"] is False
    assert env.read_text() == "SYNAPSE_TOKEN=private-sentinel\n"
    assert database.read_bytes() == b"preserved fixture"
    assert calls[-1][:6] == [str(setup.environment_python(tmp_path)), "-I", "-m", "pip", "--isolated", "install"]
    assert "--require-virtualenv" in calls[-1] and str(tmp_path / "requirements-desktop.txt") in calls[-1]
    assert not any("setup_voice_model.py" in value for command in calls for value in command)
    assert "private-sentinel" not in json.dumps(result)


def test_default_new_config_is_local_and_existing_values_survive(tmp_path, synthetic_config_io):
    assert setup.create_local_env(tmp_path)
    contents = (tmp_path / ".env").read_text()
    for key in ("INTEL_ENABLED", "REDIS_ENABLED", "SLACK_ENABLED", "JIRA_ENABLED"):
        assert key + "=false" in contents
    assert not setup.create_local_env(tmp_path)
    assert (tmp_path / ".env").read_text() == contents


def test_installation_failure_stops_before_config_or_model_download(tmp_path):
    fixture_environment(tmp_path)
    (tmp_path / "requirements-voice.txt").write_text("synthetic==1\n")
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        if "pip" in command:
            raise subprocess.CalledProcessError(1, command)
        return probe_result(tmp_path)
    with pytest.raises(setup.SetupError, match="dependency_or_model_installation_failed"):
        setup.install(tmp_path, voice=True, download_voice_model=True, runner=runner)
    assert not (tmp_path / ".env").exists()
    assert not any("setup_voice_model.py" in value for command in calls for value in command)


def test_voice_model_download_is_explicit_and_uses_project_interpreter(tmp_path, synthetic_config_io):
    fixture_environment(tmp_path)
    (tmp_path / "requirements-voice.txt").write_text("synthetic==1\n")
    commands = []
    def runner(command, **kwargs):
        commands.append(command)
        return probe_result(tmp_path)
    setup.install(tmp_path, voice=True, download_voice_model=True, runner=runner)
    assert commands[-1] == [str(setup.environment_python(tmp_path)), "-I", str(tmp_path / "scripts/setup_voice_model.py")]


def test_launcher_environment_overrides_external_adapters_without_mutating_original():
    original = {"INTEL_ENABLED": "true", "SLACK_ENABLED": "true", "SYNAPSE_TOKEN": "private", "PYTHONPATH": "foreign"}
    result = setup.local_environment(original)
    assert original["INTEL_ENABLED"] == "true" and original["PYTHONPATH"] == "foreign"
    assert result["INTEL_ENABLED"] == result["SLACK_ENABLED"] == result["JIRA_ENABLED"] == result["REDIS_ENABLED"] == "false"
    assert result["SYNAPSE_TOKEN"] == "private" and "PYTHONPATH" not in result


def test_offline_doctor_never_contacts_ollama():
    with patch.object(doctor, "build_opener", side_effect=AssertionError("network forbidden")):
        result = doctor.ollama_report(offline=True)
    assert result["checked"] is False and result["reachable"] is None


def test_doctor_requires_exact_requested_model_aliases_and_never_calls_inference():
    calls = []
    class Transport:
        def open(self, request, *, timeout):
            calls.append(request)
            return BytesIO(json.dumps({"models": [{"name": "llama3:q4"}, {"name": "mistral:latest"}, {"name": "private-model"}]}).encode())
    with patch.object(doctor, "build_opener", return_value=Transport()) as opener:
        result = doctor.ollama_report()
    assert result["reachable"] and result["missing_models"] == ["llama3"]
    assert [request.full_url for request in calls] == ["http://127.0.0.1:11434/api/tags"]
    assert "private-model" not in json.dumps(result)
    handlers = opener.call_args.args
    assert any(isinstance(handler, doctor.NoRedirect) for handler in handlers)
    assert any(getattr(handler, "proxies", None) == {} for handler in handlers)


def test_doctor_errors_do_not_echo_transport_or_config_secrets():
    with patch.object(doctor, "build_opener", side_effect=OSError("private-token-sentinel")):
        result = doctor.ollama_report()
    assert result["reachable"] is False and "private-token-sentinel" not in json.dumps(result)


def test_offline_readiness_distinguishes_installation_from_unchecked_inference(tmp_path):
    dependencies = [{"package": "fixture", "required": "1", "installed": "1", "ok": True}]
    with patch.object(doctor.sys, "prefix", str(tmp_path / ".venv")), \
         patch.object(doctor, "dependency_report", return_value=dependencies), \
         patch.object(doctor, "build_opener", side_effect=AssertionError("network forbidden")):
        result = doctor.report(root=tmp_path, offline=True)
    assert result["installation_ready"] is True
    assert result["inference_ready"] is None and result["ready"] is False


def test_online_readiness_requires_models_and_voice_files_when_requested(tmp_path):
    dependencies = [{"package": "fixture", "required": "1", "installed": "1", "ok": True}]
    models = {"checked": True, "reachable": True, "required_models": list(doctor.REQUIRED_MODELS), "missing_models": []}
    with patch.object(doctor.sys, "prefix", str(tmp_path / ".venv")), \
         patch.object(doctor, "dependency_report", return_value=dependencies), \
         patch.object(doctor, "ollama_report", return_value=models):
        assert doctor.report(root=tmp_path)["ready"] is True
        assert doctor.report(root=tmp_path, voice=True)["ready"] is False
        folder = tmp_path / "models" / doctor.MODEL_FOLDER
        folder.mkdir(parents=True)
        for part in doctor.MODEL_PARTS:
            (folder / part).write_bytes(b"fixture")
        assert doctor.report(root=tmp_path, voice=True)["ready"] is True


def test_readiness_rejects_wrong_environment_even_with_dependencies_and_models(tmp_path):
    dependencies = [{"package": "fixture", "required": "1", "installed": "1", "ok": True}]
    with patch.object(doctor.sys, "prefix", str(tmp_path / "other-environment")), \
         patch.object(doctor, "dependency_report", return_value=dependencies), \
         patch.object(doctor, "ollama_report", return_value={"checked": True, "reachable": True, "missing_models": []}):
        result = doctor.report(root=tmp_path)
    assert result["installation_ready"] is False and result["ready"] is False


def test_check_only_does_not_create_environment_or_config(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    with patch.object(setup, "ensure_environment", side_effect=AssertionError("must not mutate")):
        assert setup.main(["--no-network"]) == 1
    assert list(tmp_path.iterdir()) == []


def test_launch_command_is_loopback_and_paths_are_separate_arguments(tmp_path):
    from scripts.launch_local import launch_command
    root = tmp_path / "EAON with spaces"
    executable = root / ".venv/Scripts/python.exe"
    command = launch_command(root, executable, 8502)
    assert command[0:5] == [str(executable), "-I", "-m", "streamlit", "run"]
    assert command[5] == str(root / "ui/app.py")
    assert command[command.index("--server.address") + 1] == "127.0.0.1"
    assert command[command.index("--server.port") + 1] == "8502"


def test_launcher_fails_without_starting_ui_when_dependencies_missing(tmp_path, monkeypatch):
    from scripts import launch_local
    monkeypatch.setattr(launch_local, "ROOT", tmp_path)
    with patch.object(launch_local, "validate_environment", return_value=tmp_path / "python.exe"), \
         patch.object(launch_local.subprocess, "run", return_value=SimpleNamespace(stdout='{"installation_ready":false}', returncode=1)) as runner:
        assert launch_local.main([]) == 1
    assert runner.call_count == 1 and "doctor_local.py" in runner.call_args.args[0][2]
