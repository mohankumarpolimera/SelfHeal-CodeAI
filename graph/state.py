

class CodeState(dict):
    """
    Shared state between all agents in the graph.
    """
    user_request: str
    code: str
    errors: list
    fixed_code: str
    test_results: str
    explanation: str
