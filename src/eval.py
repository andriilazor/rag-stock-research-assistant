import json

from agent import ask

with open("data/eval_questions.json") as f:
    questions = json.load(f)

results = []
correct = 0

for q in questions:
    r = ask(q["question"])
    ok = all(f.lower() in r["answer"].lower() for f in q["key_facts"])
    correct += ok

    tools = ", ".join(sorted({t["name"] for t in r["tool_calls"]})) or "None"
    results.append(
        f"{q['id']}: {'OK' if ok else 'FAIL'} | "
        f"Latency: {r['latency_ms'] / 1000:.1f}s | Tools: {tools}\n"
        f"Answer: {r['answer']}"
    )

report = "\n\n".join(results) + f"\n\nCorrect: {correct}/{len(questions)}"

print(report)

with open("eval_results.md", "w") as f:
    f.write(report)