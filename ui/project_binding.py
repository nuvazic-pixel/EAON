"""Explicit UI transitions and user-confirmed project edits without Streamlit."""
from hashlib import sha256

from core import Orchestrator
from core.project_context import ProjectContext, ProjectContextError
from core.project_files import ProjectFileError, create_project_file, restore_backup
from eaon_kernel import ContinuityKernel, ConflictError, IntegrityError, SourceRef, ValidationError


CONTEXT_PROBLEMS = {
    "context_invalid_configuration": "Verifică fișierul proiectului, identificatorul și setările Synapse. Pentru Synapse este necesar tokenul SYNAPSE_TOKEN pe acest calculator.",
    "context_project_unavailable": "Proiectul nu este disponibil. Verifică fișierul și identificatorul proiectului.",
    "context_integrity_failed": "Jurnalul proiectului nu trece verificarea. Cererea a fost oprită înainte de model.",
    "context_owner_mismatch": "Proprietarul proiectului s-a schimbat. Reconectează proiectul după verificare.",
    "context_budget_exceeded": "Contextul proiectului este prea mare. Redu memoria activă sau selectează un proiect mai restrâns.",
    "context_retrieval_failed": "Nu pot recupera dovezile proiectului. Verifică sursa și accesul la Synapse.",
    "context_required_evidence_missing": "Lipsesc dovezi cerute pentru această conversație. Cererea a fost oprită înainte de model.",
    "context_changed_during_retrieval": "Proiectul s-a schimbat în timpul pregătirii contextului. Trimite mesajul din nou.",
    "context_requires_local_mode": "Proiectele pot fi folosite doar în conversația locală.",
    "context_state_contaminated": "Contra-dovezile au pus memoria în carantină. Revocă sau restaurează explicit înainte de a continua.",
}

FILE_PROBLEMS = {
    "project_file_invalid_path": "Alege un nume de fișier și un folder valid.",
    "project_file_exists": "Fișierul există deja. Alege un fișier nou; proiectul existent a fost păstrat.",
    "project_create_invalid": "Completează numele și identificatorul. Prima sarcină are nevoie de un obiectiv.",
    "project_create_failed": "Proiectul nu a putut fi creat. Verifică drepturile folderului.",
    "project_created_unbound": "Fișierul nou este salvat, dar nu s-a conectat. Îl poți conecta din formularul proiectului existent.",
    "backup_invalid_source": "Nu găsesc baza proiectului pentru copie.",
    "backup_integrity_failed": "Copia nu trece verificarea jurnalului și nu a fost restaurată.",
    "backup_invalid_receipt": "Copia sau fișierul ei de verificare nu este valid.",
    "backup_digest_mismatch": "Copia a fost modificată sau este incompletă. Restaurarea a fost oprită.",
    "backup_busy": "Proiectul este ocupat. Încearcă din nou copia de siguranță.",
    "backup_target_exists": "Numele copiei este deja folosit. Încearcă din nou.",
    "backup_failed": "Nu pot salva sau citi copia. Verifică folderul și drepturile lui.",
    "restore_target_exists": "Fișierul de restaurare există deja. Alege un nume nou.",
    "restore_failed": "Restaurarea nu a reușit. Originalul și copia au fost păstrate.",
    "project_not_attached": "Conectează mai întâi proiectul.",
    "project_memory_invalid": "Verifică numele, textul și dovada memoriei. Confirmarea cere o sursă păstrată sau textul și adresa unei surse noi.",
    "project_memory_conflict": "Memoria s-a schimbat între timp. Reîncarcă starea înainte de salvare.",
    "project_memory_procedural": "Procedurile și skillurile se admit prin fluxul cu traseu verificat, nu prin acest formular.",
    "project_memory_unavailable": "Memoria nu a putut fi verificată. Nu s-a confirmat nicio modificare.",
}


def reset_conversation(state):
    state["messages"] = []
    state["draft"] = ""
    state["last_recording"] = None
    state["draft_stt_ms"] = None
    state["microphone_version"] = state.get("microphone_version", 0) + 1
    state.pop("memory_editor", None)
    state.pop("memory_revoke_editor", None)


def attach_project(state, db, project_id, *, synapse_url=None, collection_id=None,
                   context_factory=None, orchestrator_factory=None):
    """Prepare and verify the replacement before mutating the current session."""
    context_factory = context_factory or ProjectContext
    orchestrator_factory = orchestrator_factory or Orchestrator
    try:
        context = context_factory(db, project_id, synapse_url=synapse_url, collection_id=collection_id)
        orchestrator = orchestrator_factory(local_only=True, context_session=context)
        context.project_card()
    except (OSError, ValueError, TypeError):
        raise ProjectContextError("context_invalid_configuration") from None
    state["project_context"] = context
    state["orchestrator"] = orchestrator
    reset_conversation(state)


def detach_project(state, *, orchestrator_factory=None):
    orchestrator = (orchestrator_factory or Orchestrator)(local_only=True)
    state["project_context"] = None
    state["orchestrator"] = orchestrator
    reset_conversation(state)


def create_and_attach_project(state, db, project_id, title, *, owner_id="local", goal="", first_task="",
                              context_factory=None, orchestrator_factory=None):
    path = create_project_file(db, project_id, title, owner_id=owner_id, goal=goal, first_task=first_task)
    try:
        attach_project(state, path, project_id, context_factory=context_factory,
                       orchestrator_factory=orchestrator_factory)
    except ProjectContextError:
        raise ProjectFileError("project_created_unbound") from None
    return path


def restore_and_attach_project(state, backup, target, project_id, *, backup_dir=None,
                               context_factory=None, orchestrator_factory=None):
    path = restore_backup(backup, target, backup_dir=backup_dir)
    try:
        attach_project(state, path, project_id, context_factory=context_factory,
                       orchestrator_factory=orchestrator_factory)
    except ProjectContextError:
        raise ProjectFileError("project_created_unbound") from None
    return path


def memory_history(state):
    context = state.get("project_context")
    if context is None:
        raise ProjectFileError("project_not_attached")
    try:
        context.project_card()
        card = ContinuityKernel(context.db).recover(context.project_id)
        if card["owner_id"] != context.owner_id:
            raise IntegrityError("owner mismatch")
        return card["memories"]
    except (ProjectContextError, IntegrityError, ValidationError, OSError):
        raise ProjectFileError("project_memory_unavailable") from None


def save_memory(state, key, value, *, status="hypothesis", source_text="", source_uri="",
                expected_revision=None, keep_existing_sources=True):
    records = memory_history(state)
    context = state["project_context"]
    if type(key) is not str or type(source_text) is not str or type(source_uri) is not str or type(keep_existing_sources) is not bool:
        raise ProjectFileError("project_memory_invalid")
    if key.split(":", 1)[0].strip().casefold() in {"skill", "procedure", "procedural"}:
        raise ProjectFileError("project_memory_procedural")
    prior = records.get(key)
    if prior and "card" in prior:
        raise ProjectFileError("project_memory_procedural")
    if (prior and expected_revision != prior["revision"]) or (not prior and expected_revision is not None):
        raise ProjectFileError("project_memory_conflict")
    try:
        sources = [SourceRef(**source) for source in prior["sources"]] if prior and keep_existing_sources else []
        if source_text or source_uri:
            if not source_text.strip() or not source_uri.strip():
                raise ValueError
            digest = sha256(source_text.encode("utf-8")).hexdigest()
            source = SourceRef("ui:" + digest, source_uri, source_text, digest)
            if source not in sources:
                sources.append(source)
        result = ContinuityKernel(context.db).record_memory(context.project_id, key, value,
                 status=status, sources=tuple(sources), expected_revision=expected_revision)
        reset_conversation(state)
        return result
    except ConflictError:
        raise ProjectFileError("project_memory_conflict") from None
    except (ValidationError, ValueError, TypeError):
        raise ProjectFileError("project_memory_invalid") from None
    except (IntegrityError, OSError):
        raise ProjectFileError("project_memory_unavailable") from None


def revoke_saved_memory(state, key, expected_revision, reason):
    memory_history(state)
    context = state["project_context"]
    try:
        result = ContinuityKernel(context.db).revoke_memory(context.project_id, key, expected_revision, reason)
        reset_conversation(state)
        return result
    except ConflictError:
        raise ProjectFileError("project_memory_conflict") from None
    except (ValidationError, ValueError, TypeError):
        raise ProjectFileError("project_memory_invalid") from None
    except (IntegrityError, OSError):
        raise ProjectFileError("project_memory_unavailable") from None
