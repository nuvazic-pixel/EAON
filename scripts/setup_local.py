"""Install EAON into this folder's Python 3.12 .venv; preserve existing data/config."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SAFE_ENV_TEXT = """# Local EAON profile; created only when .env is absent.
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=
INTEL_ENABLED=false
REDIS_ENABLED=false
SLACK_ENABLED=false
JIRA_ENABLED=false
"""


class SetupError(RuntimeError):
    pass


def local_environment(environ=None):
    env = dict(os.environ if environ is None else environ)
    for key in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(key, None)
    env.update(INTEL_ENABLED="false", REDIS_ENABLED="false", SLACK_ENABLED="false", JIRA_ENABLED="false", PYTHONNOUSERSITE="1")
    return env


def environment_python(root):
    return Path(root) / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def validate_environment(root, *, runner=subprocess.run):
    root = Path(root).resolve()
    target = root / ".venv"
    if target.resolve().parent != root or target.is_symlink():
        raise SetupError("environment_outside_project")
    python = environment_python(root)
    if not python.is_file() or not (target / "pyvenv.cfg").is_file():
        raise SetupError("environment_incomplete")
    code = "import json,sys; print(json.dumps({'version':list(sys.version_info[:2]),'prefix':sys.prefix,'base':sys.base_prefix}))"
    try:
        result = runner([str(python), "-I", "-c", code], cwd=root, env=local_environment(),
                        capture_output=True, text=True, timeout=20, check=True)
        info = json.loads(result.stdout)
        if (info.get("version") != [3, 12] or Path(info["prefix"]).resolve() != target.resolve()
                or info["prefix"] == info["base"]):
            raise SetupError("environment_requires_python_312")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise SetupError("environment_invalid") from None
    return python


def ensure_environment(root, *, runner=subprocess.run):
    root = Path(root).resolve()
    if sys.version_info[:2] != (3, 12):
        raise SetupError("run_with_py_312")
    target = root / ".venv"
    if not target.exists():
        try:
            runner([sys.executable, "-I", "-m", "venv", str(target)], cwd=root,
                   env=local_environment(), check=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            raise SetupError("environment_creation_failed") from None
    return validate_environment(root, runner=runner)


def create_local_env(root):
    path = Path(root) / ".env"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(SAFE_ENV_TEXT)
    except FileExistsError:
        return False
    return True


def install(root=ROOT, *, voice=False, download_voice_model=False, runner=subprocess.run):
    root = Path(root).resolve()
    requirements = root / ("requirements-voice.txt" if voice else "requirements-desktop.txt")
    if not requirements.is_file() or (download_voice_model and not voice):
        raise SetupError("invalid_installation_profile")
    python = ensure_environment(root, runner=runner)
    try:
        runner([str(python), "-I", "-X", "utf8", "-m", "pip", "--isolated", "install", "--require-virtualenv",
                "--disable-pip-version-check", "--no-input", "-r", str(requirements)],
               cwd=root, env=local_environment(), check=True)
        if download_voice_model:
            runner([str(python), "-I", "-X", "utf8", str(root / "scripts/setup_voice_model.py")],
                   cwd=root, env=local_environment(), check=True)
    except (OSError, subprocess.SubprocessError):
        raise SetupError("dependency_or_model_installation_failed") from None
    created_env = create_local_env(root)
    return {"ok": True, "profile": "voice" if voice else "desktop", "environment": ".venv",
            "env_file_created": created_env, "voice_model_download_requested": download_voice_model}


MESSAGES = {
    "run_with_py_312": "Rulează Instaleaza-EAON.cmd sau py -3.12 scripts\\setup_local.py.",
    "environment_requires_python_312": "Mediul .venv existent nu folosește Python 3.12. Extrage pachetul într-un folder nou; datele existente sunt păstrate.",
    "environment_incomplete": "Mediul .venv existent este incomplet. Folosește un folder nou; instalatorul nu îl șterge.",
    "environment_outside_project": "Mediul .venv trebuie să fie în folderul acestui pachet.",
    "environment_invalid": "Nu pot valida mediul .venv. Folosește un folder nou pentru instalare.",
    "environment_creation_failed": "Nu am putut crea mediul local. Verifică Python 3.12 și dreptul de scriere în acest folder.",
    "invalid_installation_profile": "Profilul sau fișierul de dependențe nu este valid.",
    "dependency_or_model_installation_failed": "Instalarea nu s-a încheiat. Verifică mesajele de mai sus și conexiunea; configurația și bazele existente sunt păstrate.",
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", action="store_true", help="Install optional Sherpa/NumPy voice packages")
    parser.add_argument("--download-voice-model", action="store_true", help="Explicitly download the existing Sherpa tiny model; requires --voice")
    parser.add_argument("--check-only", action="store_true", help="Read-only readiness check; no installation/config changes")
    parser.add_argument("--no-network", action="store_true", help="Read-only check without even contacting local Ollama")
    args = parser.parse_args(argv)
    if args.download_voice_model and (not args.voice or args.check_only or args.no_network):
        parser.error("--download-voice-model requires --voice and an actual installation")
    try:
        if args.check_only or args.no_network:
            python = validate_environment(ROOT)
            command = [str(python), "-I", str(ROOT / "scripts/doctor_local.py")]
            if args.voice:
                command.append("--voice")
            if args.no_network:
                command.append("--offline")
            return subprocess.run(command, cwd=ROOT, env=local_environment(), check=False).returncode
        if sys.version_info[:2] != (3, 12):
            raise SetupError("run_with_py_312")
        print("Instalez EAON în mediul local .venv. Modelele Ollama nu sunt descărcate automat.", flush=True)
        result = install(voice=args.voice, download_voice_model=args.download_voice_model)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("Instalarea s-a încheiat. Pornește Ollama, apoi deschide Porneste-EAON.cmd.")
        print("Modelele necesare sunt llama3 și mistral. Verificare: .venv\\Scripts\\python.exe scripts\\doctor_local.py")
        return 0
    except SetupError as exc:
        print(MESSAGES.get(str(exc), "Instalarea nu poate continua."), file=sys.stderr)
        return 1
    except OSError:
        print("Nu pot scrie configurația locală. Fișierele existente sunt păstrate.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
