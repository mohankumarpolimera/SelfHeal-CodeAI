# agents/learner.py
class LearnerAgent:
    def learn_patterns(self, state: dict):
        state.setdefault("debug", []).append({"node": "learner", "attempts": int(state.get("attempts", 0))})
        errors = state.get("errors") or []
        patterns = state.get("learner_patterns") or {}
        if errors:
            for e in errors:
                key = (str(e)[:80] or "unknown").strip()
                patterns[key] = patterns.get(key, 0) + 1
        state["learner_patterns"] = patterns
        return state
