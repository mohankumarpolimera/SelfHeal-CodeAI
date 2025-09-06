from langgraph.graph import StateGraph, END
from graph.state import CodeState
from agents.code_generator import CodeGeneratorAgent
from agents.validator import ValidatorAgent
from agents.error_analyzer import ErrorAnalyzerAgent
from agents.fixer import FixerAgent
from agents.memory import MemoryAgent
from agents.learner import LearnerAgent


DEFAULT_MAX_ATTEMPTS = 3


def _bump_attempts(state: CodeState) -> CodeState:
    """Internal node: increment loop attempts after each fix."""
    state["attempts"] = int(state.get("attempts", 0)) + 1
    return state


def _route_after_analyze(state: CodeState) -> str:
    """
    Router for 'analyze' node:
      - If runtime/test errors exist -> 'fail' (go fix)
      - Else -> 'pass' (go validate)
    """
    errs = state.get("errors") or []
    return "fail" if len(errs) > 0 else "pass"


def _route_after_validate(state: CodeState) -> str:
    """
    Router for 'validate' node:
      - If validated True            -> 'pass'   (go memory)
      - Else if attempts exhausted   -> 'giveup' (store anyway, then END)
      - Else                         -> 'fail'   (go fix and try again)
    """
    if state.get("validated", False):
        return "pass"

    attempts = int(state.get("attempts", 0))
    max_attempts = int(state.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
    if attempts >= max_attempts:
        return "giveup"

    return "fail"


def build_graph():
    """
    Build & compile the agentic workflow:

      generate → analyze → (fail → fix → bump → analyze | pass → validate)
      validate → (pass → memory → learner → END | fail → fix → bump → analyze | giveup → memory → learner → END)
    """
    # Initialize agents (must implement the following signatures):
    # - CodeGenerator.generate_code(state) -> sets state["code"]
    # - ErrorAnalyzer.analyze_error(state) -> sets state["errors"] (list), may set state["analyzer_output"]
    # - Fixer.fix_code(state)             -> updates state["code"], append a summary in state["fix_attempts"]
    # - Validator.validate_code(state)    -> sets state["validated"] (bool) and state["validation_issues"] (list)
    # - MemoryAgent.store_experience(s)   -> persists request/errors/fixes/final_code; returns state unchanged
    # - LearnerAgent.learn_patterns(s)    -> sets state["learner_patterns"] (dict)

    generator = CodeGeneratorAgent()
    analyzer = ErrorAnalyzerAgent()
    fixer = FixerAgent()
    validator = ValidatorAgent(
                sandbox_url="http://127.0.0.1:8001",
                tester_url="http://127.0.0.1:8002",
            )
    memory = MemoryAgent(memory_url="http://127.0.0.1:8005")
    learner = LearnerAgent()

    g = StateGraph(CodeState)

    # Agent nodes
    g.add_node("generate", generator.generate_code)
    g.add_node("analyze", analyzer.analyze_error)
    g.add_node("fix", fixer.fix_code)
    g.add_node("bump", _bump_attempts)  # internal helper node
    g.add_node("validate", validator.validate_code)
    g.add_node("memory", memory.store)
    g.add_node("learner", learner.learn_patterns)

    # Entry
    g.set_entry_point("generate")

    # Flow
    g.add_edge("generate", "analyze")

    # analyze -> (pass: validate | fail: fix)
    g.add_conditional_edges(
        "analyze",
        _route_after_analyze,
        {
            "pass": "validate",
            "fail": "fix",
        },
    )

    # after fix, bump attempts then analyze again
    g.add_edge("fix", "bump")
    g.add_edge("bump", "analyze")

    # validate -> (pass: memory | fail: fix | giveup: memory)
    g.add_conditional_edges(
        "validate",
        _route_after_validate,
        {
            "pass": "memory",
            "fail": "fix",
            "giveup": "memory",
        },
    )

    # wrap up
    g.add_edge("memory", "learner")
    g.add_edge("learner", END)

    return g.compile()


def execute_selfheal(user_request: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> dict:
    """
    Convenience runner used by the FastAPI /run endpoint.
    Returns a JSON-serializable dict for the frontend.
    """
    executor = build_graph()

    # initialize shared state
    state = CodeState({
        "user_request": user_request,
        "code": "",
        "errors": [],
        "fix_attempts": [],
        "validated": False,
        "validation_issues": [],
        "analyzer_output": None,
        "learner_patterns": {},
        "attempts": 0,
        "max_attempts": max_attempts,
    })

    # Run the compiled graph until END (LangGraph will follow edges/routers)
    final = executor.invoke(state)

    # Normalize the response for the frontend
    return {
        "code": final.get("code", ""),
        "errors": final.get("errors", []),
        "fix_attempts": final.get("fix_attempts", []),
        "final_code": final.get("code", ""),
        "validated": final.get("validated", False),
        "validation_issues": final.get("validation_issues", []),
        "learner_patterns": final.get("learner_patterns", {}),
        "attempts": final.get("attempts", 0),
        "max_attempts": final.get("max_attempts", max_attempts),
    }
