def make_module_boundary(name: str, responsibility: str, inputs: list[str], outputs: list[str]) -> dict:
    return {
        'module': name,
        'responsibility': responsibility,
        'inputs': inputs,
        'outputs': outputs,
    }


def estimate_complexity(modules: list[dict]) -> str:
    count = len(modules)

    if count <= 3:
        return 'low'
    if count <= 7:
        return 'medium'
    return 'high'
