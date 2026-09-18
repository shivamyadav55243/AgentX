from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.image_gen import generate_header_image
from agents.planner import plan
from agents.researcher import research
from agents.writer import write_report
from storage.memory import save_report
from agents.critic import review_report

# Keep Gemini calls sequential; free tier is 5 requests/minute.
# Tavily search still happens inside each worker before the shared LLM lock.
MAX_RESEARCH_WORKERS = 2
MAX_CRITIC_REVISIONS = 1


def _emit(on_progress, message):
    print(message)
    if on_progress:
        on_progress(message)


def _approved(review):
    return review.strip().upper().startswith("APPROVED")


def run_pipeline(topic, on_progress=None):
    header_image = None
    _emit(on_progress, f"Planning research for: {topic}")
    sub_questions = plan(topic)

    _emit(
        on_progress,
        f"Planner split this into {len(sub_questions)} sub-questions",
    )
    for q in sub_questions:
        print(f"  - {q}")

    findings = [None] * len(sub_questions)
    failed_count = 0
    completed = 0
    workers = max(1, min(MAX_RESEARCH_WORKERS, len(sub_questions)))

    _emit(on_progress, f"Researching 0/{len(sub_questions)} in parallel…")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(research, q): (i, q)
            for i, q in enumerate(sub_questions)
        }
        for future in as_completed(futures):
            i, q = futures[future]
            result = future.result()
            findings[i] = (q, result)
            completed += 1
            if result["answer"].startswith("[Research failed"):
                failed_count += 1
            _emit(
                on_progress,
                f"Researching {completed}/{len(sub_questions)}: {q}",
            )

    if failed_count > 0:
        _emit(
            on_progress,
            f"Note: {failed_count} of {len(sub_questions)} sub-questions failed",
        )

    _emit(on_progress, "Writing the final report…")
    report = write_report(topic, findings)

    writer_fell_back = "AI writer unavailable" in report
    if writer_fell_back:
        _emit(on_progress, "Skipping critic because the writer used the fallback draft")
        _emit(on_progress, "Generating header image…")
        header_image = generate_header_image(topic)
        save_report(topic, report, image=header_image)
        print("=" * 60)
        print(report)
        print("=" * 60)
        _emit(on_progress, "Research complete")
        return report, header_image

    _emit(on_progress, "Fact-checking the report…")
    review = review_report(topic, report)
    print(f"Critic feedback: {review}\n")

    revisions = 0
    while not _approved(review) and revisions < MAX_CRITIC_REVISIONS:
        revisions += 1
        _emit(on_progress, "Revising the report from critic notes…")
        report = write_report(topic, findings, revision_notes=review)
        _emit(on_progress, "Re-checking the revised report…")
        review = review_report(topic, report)
        print(f"Critic feedback (revision {revisions}): {review}\n")

    if not _approved(review):
        report += f"\n\n---\n**Reviewer notes:**\n{review}"

    _emit(on_progress, "Generating header image…")
    header_image = generate_header_image(topic)

    save_report(topic, report, image=header_image)

    print("=" * 60)
    print(report)
    print("=" * 60)

    _emit(on_progress, "Research complete")
    return report, header_image


if __name__ == "__main__":
    topic = input("Enter a topic to research: ")
    run_pipeline(topic)