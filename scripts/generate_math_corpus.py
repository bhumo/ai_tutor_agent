"""Deterministically build the 500-item linear-algebra and geometry Q&A corpus."""

from __future__ import annotations

import json
from pathlib import Path


CORPUS_PATH = Path(__file__).resolve().parents[1] / "rag" / "data" / "knowledge.json"
GENERATED_PREFIXES = ("la-", "geo-")


def record(identifier: str, topic: str, question: str, answer: str,
           difficulty: str = "beginner") -> dict[str, str]:
    return {
        "id": identifier,
        "domain": "math",
        "topic": topic,
        "question": question,
        "answer": answer,
        "difficulty": difficulty,
    }


def linear_algebra_questions() -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []

    for index in range(80):
        coefficient = 2 + index % 19
        solution = index + 1
        offset = index * 3 % 23
        total = coefficient * solution + offset
        questions.append(record(
            f"la-equation-{index + 1:03d}", "linear algebra - linear equations",
            f"Solve {coefficient}x + {offset} = {total}.",
            f"Subtract {offset} from both sides to get {coefficient}x = {coefficient * solution}, "
            f"then divide by {coefficient}. Therefore x = {solution}.",
        ))

    for index in range(50):
        left = (index + 1, index % 9 - 4)
        right = (index % 7 + 2, 2 * index % 11 - 5)
        result = (left[0] + right[0], left[1] + right[1])
        questions.append(record(
            f"la-vector-add-{index + 1:03d}", "linear algebra - vectors",
            f"Add the vectors ({left[0]}, {left[1]}) and ({right[0]}, {right[1]}).",
            f"Add corresponding components: ({left[0]} + {right[0]}, {left[1]} + {right[1]}) "
            f"= ({result[0]}, {result[1]}).",
        ))

    for index in range(40):
        left = (index % 13 + 1, index % 7 - 3)
        right = (index % 5 + 2, index % 11 - 5)
        value = left[0] * right[0] + left[1] * right[1]
        questions.append(record(
            f"la-dot-product-{index + 1:03d}", "linear algebra - dot products",
            f"Find the dot product of ({left[0]}, {left[1]}) and ({right[0]}, {right[1]}).",
            f"Multiply corresponding components and add: {left[0]}({right[0]}) + "
            f"{left[1]}({right[1]}) = {value}.",
            "intermediate",
        ))

    for index in range(40):
        a, b = index % 11 + 1, index % 7 - 3
        c, d = index % 5 + 2, index % 13 - 6
        determinant = a * d - b * c
        questions.append(record(
            f"la-determinant-{index + 1:03d}", "linear algebra - matrices",
            f"Find the determinant of the matrix [[{a}, {b}], [{c}, {d}]].",
            f"For [[a, b], [c, d]], the determinant is ad - bc. Here it is "
            f"{a}({d}) - {b}({c}) = {determinant}.",
            "intermediate",
        ))

    for index in range(40):
        a, b = index % 9 + 1, index % 6 - 2
        c, d = index % 8 + 2, index % 10 - 4
        trace = a + d
        questions.append(record(
            f"la-matrix-trace-{index + 1:03d}", "linear algebra - matrices",
            f"Find the trace of the matrix [[{a}, {b}], [{c}, {d}]].",
            f"The trace is the sum of the main diagonal entries: {a} + {d} = {trace}.",
            "intermediate",
        ))

    return questions


def geometry_questions() -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []

    for index in range(50):
        length, width = index + 3, index % 12 + 2
        questions.append(record(
            f"geo-rectangle-{index + 1:03d}", "geometry - rectangles",
            f"A rectangle has length {length} units and width {width} units. Find its area and perimeter.",
            f"Area = length × width = {length * width} square units. Perimeter = "
            f"2(length + width) = {2 * (length + width)} units.",
        ))

    for index in range(50):
        base, height = 2 * (index + 2), index % 15 + 3
        questions.append(record(
            f"geo-triangle-area-{index + 1:03d}", "geometry - triangles",
            f"Find the area of a triangle with base {base} units and height {height} units.",
            f"Area = one half × base × height = 1/2 × {base} × {height} = "
            f"{base * height // 2} square units.",
        ))

    for index in range(50):
        radius = index + 1
        questions.append(record(
            f"geo-circle-{index + 1:03d}", "geometry - circles",
            f"A circle has radius {radius} units. Find its exact area and circumference.",
            f"Area = πr² = {radius * radius}π square units. Circumference = 2πr = "
            f"{2 * radius}π units.",
        ))

    for index in range(50):
        scale, x, y = index % 10 + 1, index - 20, index % 17 - 8
        x2, y2 = x + 3 * scale, y + 4 * scale
        questions.append(record(
            f"geo-distance-{index + 1:03d}", "geometry - coordinate plane",
            f"Find the distance between ({x}, {y}) and ({x2}, {y2}).",
            f"Using the distance formula gives √(({x2} - {x})² + ({y2} - {y})²) "
            f"= √(({3 * scale})² + ({4 * scale})²) = {5 * scale} units.",
            "intermediate",
        ))

    for index in range(50):
        scale = index + 1
        leg_a, leg_b, hypotenuse = 3 * scale, 4 * scale, 5 * scale
        questions.append(record(
            f"geo-pythagorean-{index + 1:03d}", "geometry - right triangles",
            f"A right triangle has legs {leg_a} and {leg_b} units. Find the hypotenuse.",
            f"By the Pythagorean theorem, c = √({leg_a}² + {leg_b}²) = "
            f"√{hypotenuse * hypotenuse} = {hypotenuse} units.",
        ))

    return questions


def main() -> None:
    existing = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    retained = [
        item for item in existing
        if not item["id"].startswith(GENERATED_PREFIXES)
    ]
    generated = linear_algebra_questions() + geometry_questions()
    if len(generated) != 500:
        raise RuntimeError(f"Expected 500 generated questions, got {len(generated)}")
    CORPUS_PATH.write_text(
        json.dumps(retained + generated, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(retained) + len(generated)} records ({len(generated)} generated).")


if __name__ == "__main__":
    main()
