from agents.llm import generate_text


def _append_sources(report, all_sources):
    if not all_sources:
        return report
    seen_urls = set()
    report += "\n\n---\n## Sources\n"
    for s in all_sources:
        if s["url"] not in seen_urls:
            report += f"- [{s['title']}]({s['url']})\n"
            seen_urls.add(s["url"])
    return report


def write_report(topic, findings, revision_notes=None, max_retries=5):
    findings_text = ""
    all_sources = []
    for q, result in findings:
        findings_text += f"\n\nQ: {q}\nA: {result['answer']}"
        all_sources.extend(result.get("sources", []))

    prompt = f"""You are writing a final research report on: {topic}

Here is the raw research gathered:
{findings_text}

Combine this into one clear, well-organized report with a short intro,
organized sections, and a brief conclusion. Avoid repeating the raw Q&A format.
Do not add a sources section yourself — that will be appended separately."""

    if revision_notes:
        prompt += f"""

A reviewer found issues with a previous draft. Rewrite the report to address
these notes. Keep the same overall structure and stay faithful to the research.

Reviewer notes:
{revision_notes}"""

    try:
        report = generate_text(prompt, max_retries=max_retries)
        return _append_sources(report, all_sources)
    except Exception as e:
        print(f"⚠️ Writer failed: {e}")
        fallback = (
            f"# Report on {topic}\n\n"
            "(Note: AI writer unavailable — showing raw research)\n\n"
            + findings_text
        )
        return _append_sources(fallback, all_sources)
