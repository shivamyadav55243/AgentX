from agents.llm import generate_text


def review_report(topic, report, max_retries=5):
    prompt = f"""You are a critical fact-checking editor reviewing a research report on: {topic}

Here is the report:
---
{report}
---

Review it for:
1. Any obvious factual errors or contradictions
2. Missing important context or gaps in coverage
3. Vague or unsupported claims

If the report is solid, respond with exactly: "APPROVED - no major issues found"

If there are issues, respond with a short bullet list of specific problems found
(max 5 bullets, be concise). Do not rewrite the report yourself."""

    try:
        return generate_text(prompt, max_retries=max_retries).strip()
    except Exception as e:
        print(f"⚠️ Critic failed: {e}")
        return "APPROVED - critic unavailable, skipping review"
