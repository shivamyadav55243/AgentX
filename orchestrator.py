from agents.planner import plan
from agents.researcher import research
from agents.writer import write_report
from storage.memory import save_report

def run_pipeline(topic):
    print(f"\n🧠 Planning research for: {topic}\n")
    sub_questions = plan(topic)

    print(f"Planner decided this topic needs {len(sub_questions)} sub-questions:")
    for q in sub_questions:
        print(f"  - {q}")

    findings = []
    failed_count = 0

    for i, q in enumerate(sub_questions, 1):
        print(f"\n🔍 [{i}/{len(sub_questions)}] Researching: {q}")
        answer = research(q)
        if answer.startswith("[Research failed"):
            failed_count += 1
        findings.append((q, answer))

    if failed_count > 0:
        print(f"\n⚠️ Note: {failed_count} out of {len(sub_questions)} sub-questions failed to research.")

    print("\n✍️ Writing final report...\n")
    report = write_report(topic, findings)
    save_report(topic, report)

    print("=" * 60)
    print(report)
    print("=" * 60)

    return report

if __name__ == "__main__":
    topic = input("Enter a topic to research: ")
    run_pipeline(topic)