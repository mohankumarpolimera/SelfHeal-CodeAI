from langgraph.graph import StateGraph, END
from graph.state import CodeState

# Keep your MCP-agent class names
from agents.code_generator import CodeGeneratorAgent
from agents.validator import ValidatorAgent
from agents.error_analyzer import ErrorAnalyzerAgent
from agents.fixer import FixerAgent
from agents.memory import MemoryAgent
from agents.learner import LearnerAgent


DEFAULT_MAX_ATTEMPTS = 3


def _bump_attempts(state: CodeState) -> CodeState:
    """Increment loop attempts after each fix."""
    state["attempts"] = int(state.get("attempts", 0)) + 1
    return state


def _route_after_analyze(state: CodeState) -> str:
    """
    If runtime/test errors exist -> 'fail' (go fix)
    Else -> 'pass' (go validate)
    """
    errs = state.get("errors") or []
    return "fail" if len(errs) > 0 else "pass"


def _hard_validation_issue(issues) -> bool:
    """
    Heuristic: treat only real errors as 'hard' (blockers).
    Style nits should not block the pipeline.
    """
    if not issues:
        return False
    HARD_KWS = ("Syntax", "Error", "Exception", "ImportError", "NameError", "ModuleNotFoundError")
    for it in issues:
        if not isinstance(it, str):
            it = str(it)
        if any(kw in it for kw in HARD_KWS):
            return True
    return False


def _route_after_validate(state: CodeState) -> str:
    """
    - If validator says validated -> 'pass'
    - Else if only warnings (no 'hard' issues) -> upgrade to pass
    - Else if attempts exhausted -> 'giveup'
    - Else -> 'fail'
    """
    if state.get("validated", False):
        return "pass"

    issues = state.get("validation_issues") or []
    # Treat non-hard issues as warnings → allow pass
    if not _hard_validation_issue(issues):
        # convert issues to warnings and allow pass
        existing_warns = state.get("validation_warnings") or []
        state["validation_warnings"] = existing_warns + issues
        state["validation_issues"] = []
        state["validated"] = True
        return "pass"

    attempts = int(state.get("attempts", 0))
    max_attempts = int(state.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
    if attempts >= max_attempts:
        return "giveup"

    return "fail"


def _route_after_bump(state: CodeState) -> str:
    """
    After each fix, either loop back to analyze or give up to memory if attempts hit cap.
    This prevents infinite analyze<->fix loops before validate ever runs.
    """
    attempts = int(state.get("attempts", 0))
    max_attempts = int(state.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
    return "giveup" if attempts >= max_attempts else "again"


def build_graph():
    """
    Workflow:

      generate → analyze → (fail → fix → bump → (again → analyze | giveup → memory) | pass → validate)
      validate → (pass → memory → learner → END | fail → fix → bump → ... | giveup → memory → learner → END)
    """
    generator = CodeGeneratorAgent()
    analyzer  = ErrorAnalyzerAgent()
    fixer     = FixerAgent()
    validator = ValidatorAgent(
        sandbox_url="http://127.0.0.1:8001",
        tester_url="http://127.0.0.1:8002",
    )
    memory    = MemoryAgent(memory_url="http://127.0.0.1:8005")
    learner   = LearnerAgent()

    g = StateGraph(CodeState)

    # Nodes
    g.add_node("generate",  generator.generate_code)
    g.add_node("analyze",   analyzer.analyze_error)
    g.add_node("fix",       fixer.fix_code)
    g.add_node("bump",      _bump_attempts)   # internal
    g.add_node("validate",  validator.validate_code)
    g.add_node("memory",    memory.store)
    g.add_node("learner",   learner.learn_patterns)

    # Entry
    g.set_entry_point("generate")

    # Flow
    g.add_edge("generate", "analyze")

    # analyze -> (pass: validate | fail: fix)
    g.add_conditional_edges(
        "analyze",
        _route_after_analyze,
        {"pass": "validate", "fail": "fix"},
    )

    # fix -> bump -> (again: analyze | giveup: memory)
    g.add_edge("fix", "bump")
    g.add_conditional_edges(
        "bump",
        _route_after_bump,
        {"again": "analyze", "giveup": "memory"},
    )

    # validate -> (pass: memory | fail: fix | giveup: memory)
    g.add_conditional_edges(
        "validate",
        _route_after_validate,
        {"pass": "memory", "fail": "fix", "giveup": "memory"},
    )

    # wrap
    g.add_edge("memory", "learner")
    g.add_edge("learner", END)

    return g.compile()


def execute_selfheal(user_request: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> dict:
    """
    Runner used by FastAPI /run.
    """
    executor = build_graph()

    state = CodeState({
        "user_request": user_request,
        "code": "",
        "errors": [],
        "fix_attempts": [],
        "validated": False,
        "validation_issues": [],
        "validation_warnings": [],
        "analyzer_output": None,
        "learner_patterns": {},
        "attempts": 0,
        "max_attempts": max_attempts,
    })

    # bump recursion limit for safety; real stop is via our bump router
    final = executor.invoke(state, config={"recursion_limit": 200})

    return {
        "code": final.get("code", ""),
        "errors": final.get("errors", []),
        "fix_attempts": final.get("fix_attempts", []),
        "final_code": final.get("code", ""),
        "validated": final.get("validated", False),
        "validation_issues": final.get("validation_issues", []),
        "validation_warnings": final.get("validation_warnings", []),
        "learner_patterns": final.get("learner_patterns", {}),
        "attempts": final.get("attempts", 0),
        "max_attempts": final.get("max_attempts", max_attempts),
    }
