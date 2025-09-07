# graph/selfheal_graph.py
import os
from langgraph.graph import StateGraph, END
from graph.state import CodeState

from agents.code_generator import CodeGeneratorAgent
from agents.validator import ValidatorAgent
from agents.error_analyzer import ErrorAnalyzerAgent
from agents.fixer import FixerAgent
from agents.memory import MemoryAgent
from agents.learner import LearnerAgent

DEFAULT_MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "3"))

def _bump_attempts(state: CodeState) -> CodeState:
    state["attempts"] = int(state.get("attempts", 0)) + 1
    return state

def _hard_validation_issue(issues) -> bool:
    if not issues:
        return False
    HARD_KWS = ("Syntax", "Error", "Exception", "ImportError", "NameError", "ModuleNotFoundError")
    return any(any(kw in str(it) for kw in HARD_KWS) for it in issues)

def _route_after_analyze(state: CodeState) -> str:
    return "fail" if state.get("errors") else "pass"

def _route_after_validate(state: CodeState) -> str:
    if state.get("force_giveup"):
        return "giveup"
    if state.get("validated", False):
        return "pass"
    issues = state.get("validation_issues") or []
    if not _hard_validation_issue(issues):
        warns = state.get("validation_warnings") or []
        state["validation_warnings"] = warns + issues
        state["validation_issues"] = []
        state["validated"] = True
        return "pass"
    attempts = int(state.get("attempts", 0))
    max_attempts = int(state.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
    return "giveup" if attempts >= max_attempts else "fail"

def _route_after_bump(state: CodeState) -> str:
    if state.get("force_giveup"):
        return "giveup"
    attempts = int(state.get("attempts", 0))
    max_attempts = int(state.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
    return "giveup" if attempts >= max_attempts else "again"

def build_graph():
    generator = CodeGeneratorAgent()
    analyzer  = ErrorAnalyzerAgent()
    fixer     = FixerAgent()
    validator = ValidatorAgent()  # syntax-only
    memory    = MemoryAgent(memory_url="http://127.0.0.1:8005")
    learner   = LearnerAgent()

    g = StateGraph(CodeState)

    g.add_node("generate",  generator.generate_code)
    g.add_node("analyze",   analyzer.analyze_error)
    g.add_node("fix",       fixer.fix_code)
    g.add_node("bump",      _bump_attempts)
    g.add_node("validate",  validator.validate_code)
    g.add_node("memory",    memory.store)
    g.add_node("learner",   learner.learn_patterns)

    g.set_entry_point("generate")

    g.add_edge("generate", "analyze")

    g.add_conditional_edges("analyze", _route_after_analyze, {
        "pass": "validate",    # tests ok (or no tests): go validate syntax
        "fail": "fix",         # tests failed: go fix
    })

    g.add_edge("fix", "bump")
    g.add_conditional_edges("bump", _route_after_bump, {
        "again": "analyze",    # try again until attempts exhausted
        "giveup": "memory",
    })

    g.add_conditional_edges("validate", _route_after_validate, {
        "pass": "memory",
        "fail": "fix",
        "giveup": "memory",
    })

    g.add_edge("memory", "learner")
    g.add_edge("learner", END)

    return g.compile()

def execute_selfheal(user_request: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> dict:
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
        "references": {},
        "learner_patterns": {},
        "program_output": "",
        "attempts": 0,
        "max_attempts": max_attempts,
        "debug": [],
    })

    # Low recursion; control loop with attempts & loop-guards
    final = executor.invoke(state, config={"recursion_limit": 40})

    return {
        "code": final.get("code", ""),
        "final_code": final.get("code", ""),
        "program_output": final.get("program_output", ""),
        "validated": final.get("validated", False),
        "errors": final.get("errors", []),
        "fix_attempts": final.get("fix_attempts", []),
        "validation_issues": final.get("validation_issues", []),
        "validation_warnings": final.get("validation_warnings", []),
        "references": final.get("references", {}),
        "learner_patterns": final.get("learner_patterns", {}),
        "attempts": final.get("attempts", 0),
        "max_attempts": final.get("max_attempts", max_attempts),
        "debug": final.get("debug", []),
    }
