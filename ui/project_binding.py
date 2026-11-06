"""UI session transitions without Streamlit dependencies or journal writes."""
from core import Orchestrator
from core.project_context import ProjectContext, ProjectContextError


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
}


def reset_conversation(state):
    state["messages"] = []
    state["draft"] = ""
    state["last_recording"] = None
    state["draft_stt_ms"] = None
    state["microphone_version"] = state.get("microphone_version", 0) + 1


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
