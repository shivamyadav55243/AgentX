import os
from dotenv import load_dotenv
from tavily import TavilyClient
from agents.llm import generate_text

load_dotenv()
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def research(sub_question, max_retries=5):
    sources = []
    search_context = ""
    try:
        search_results = tavily_client.search(sub_question, max_results=4)
        for r in search_results.get("results", []):
            search_context += f"\nSource: {r['title']} ({r['url']})\n{r['content']}\n"
            sources.append({"title": r["title"], "url": r["url"]})
    except Exception as e:
        print(f"⚠️ Web search failed for '{sub_question}': {e}")
        search_context = "(No web search results available — using general knowledge.)"

    prompt = f"""Based on the following web search results, give a concise,
factual answer to this question: {sub_question}

Search results:
{search_context}

Write a clear answer using only information from these sources.
Do not include a sources list yourself, that will be added separately."""

    try:
        answer = generate_text(prompt, max_retries=max_retries)
        return {"answer": answer, "sources": sources}
    except Exception as e:
        print(f"⚠️ Researcher failed for '{sub_question}': {e}")
        return {
            "answer": f"[Research failed for this question: {e}]",
            "sources": sources,
        }
