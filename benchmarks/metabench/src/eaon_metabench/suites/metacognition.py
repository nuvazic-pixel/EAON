from __future__ import annotations

import random
from collections.abc import Callable

from eaon_metabench.models import BenchmarkCase


CONTRACT = """
Return only JSON using:
{"decision":"answer|abstain","answer":"...","confidence":0.0,"reason":"..."}
""".strip()


def _insufficient_case(rng: random.Random, index: int) -> BenchmarkCase:
    names = ["Ana", "Mara", "Liam", "Noah", "Sofia", "David"]
    name = rng.choice(names)
    known = rng.randint(2, 9)
    prompt = f"""{name} has {known} blue tokens. The task does not state how many red tokens {name} has.
Question: How many tokens does {name} have in total?
Do not estimate or assume a number that is not provided.
{CONTRACT}"""
    return BenchmarkCase(
        case_id=f"insufficient-{index:04d}",
        category="insufficient_information",
        prompt=prompt,
        expected_decision="abstain",
        metadata={"known_blue_tokens": known},
    )


def _sufficient_control_case(rng: random.Random, index: int) -> BenchmarkCase:
    blue = rng.randint(2, 12)
    red = rng.randint(1, 12)
    total = blue + red
    prompt = f"""A box contains {blue} blue tokens and {red} red tokens.
Question: How many tokens are in the box in total?
{CONTRACT}"""
    return BenchmarkCase(
        case_id=f"sufficient-{index:04d}",
        category="insufficient_information",
        prompt=prompt,
        expected_decision="answer",
        accepted_answers=(str(total),),
        metadata={"blue": blue, "red": red},
    )


def _contradiction_case(rng: random.Random, index: int) -> BenchmarkCase:
    person = rng.choice(["Alex", "Mira", "Jonas", "Nora"])
    age = rng.randint(20, 60)
    other_age = age + rng.choice([-4, -3, 3, 5])
    prompt = f"""Evaluate the consistency of these statements:
1. {person} is exactly {age} years old today.
2. {person} is exactly {other_age} years old today.
Both statements refer to the same person and the same date.
Answer with exactly CONSISTENT or INCONSISTENT.
{CONTRACT}"""
    return BenchmarkCase(
        case_id=f"contradiction-{index:04d}",
        category="contradiction_detection",
        prompt=prompt,
        expected_decision="answer",
        accepted_answers=("INCONSISTENT",),
        metadata={"age_a": age, "age_b": other_age},
    )


def _consistent_control_case(rng: random.Random, index: int) -> BenchmarkCase:
    value = rng.randint(3, 20)
    doubled = value * 2
    prompt = f"""Evaluate the consistency of these statements:
1. The number is {value}.
2. Twice the number is {doubled}.
Answer with exactly CONSISTENT or INCONSISTENT.
{CONTRACT}"""
    return BenchmarkCase(
        case_id=f"consistent-{index:04d}",
        category="contradiction_detection",
        prompt=prompt,
        expected_decision="answer",
        accepted_answers=("CONSISTENT",),
        metadata={"value": value},
    )


def _rule_shift_case(rng: random.Random, index: int) -> BenchmarkCase:
    items = ["circle", "triangle", "square", "star"]
    target = rng.choice(items)
    old_labels = {item: item.upper()[0] for item in items}
    new_label = rng.choice(["Z", "Q", "X", "M"])
    while new_label == old_labels[target]:
        new_label = rng.choice(["Z", "Q", "X", "M"])
    prompt = f"""Initial rule: encode each shape using its first letter in uppercase.
Under the initial rule, {target} would be encoded as {old_labels[target]}.
UPDATED RULE: from now on, encode {target} as {new_label}. The updated rule overrides the initial rule.
Question: Encode {target} using the rule currently in force.
Return only the encoded symbol in the answer field.
{CONTRACT}"""
    return BenchmarkCase(
        case_id=f"rule-shift-{index:04d}",
        category="rule_shift",
        prompt=prompt,
        expected_decision="answer",
        accepted_answers=(new_label,),
        metadata={"target": target, "old": old_labels[target], "new": new_label},
    )


def _error_repair_case(rng: random.Random, index: int) -> BenchmarkCase:
    a = rng.randint(3, 15)
    b = rng.randint(3, 15)
    correct = a * b
    wrong = correct + rng.choice([-3, -2, 2, 4])
    prompt = f"""A previous solver claimed: {a} × {b} = {wrong}.
Check the claim. If it is wrong, repair it and return the correct numeric result.
Do not repeat the incorrect result.
{CONTRACT}"""
    return BenchmarkCase(
        case_id=f"repair-{index:04d}",
        category="error_repair",
        prompt=prompt,
        expected_decision="answer",
        accepted_answers=(str(correct),),
        metadata={"a": a, "b": b, "wrong": wrong, "correct": correct},
    )


_GENERATORS: tuple[Callable[[random.Random, int], BenchmarkCase], ...] = (
    _insufficient_case,
    _sufficient_control_case,
    _contradiction_case,
    _consistent_control_case,
    _rule_shift_case,
    _error_repair_case,
)


def generate_metacognition_suite(count: int = 36, seed: int = 42) -> list[BenchmarkCase]:
    if count < 6:
        raise ValueError("At least 6 cases are required to cover every task type.")

    rng = random.Random(seed)
    cases: list[BenchmarkCase] = []
    for index in range(count):
        generator = _GENERATORS[index % len(_GENERATORS)]
        cases.append(generator(rng, index))
    rng.shuffle(cases)
    return cases
