import os
from google import genai
from pipeline.state import AgentState

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


async def code_writer(state: AgentState) -> dict:
    """
    Agent 3 — Code Writer
    Input state keys used:  issue_title, issue_body, relevant_files, plan
    Output key returned:    patch (unified diff string)
    """
    files_text = "\n\n".join(
        f"=== {f['path']} ===\n{f['content']}"
        for f in state["relevant_files"]
    )

    comments_text = "\n".join(f"- {c}" for c in state.get("issue_comments", []))

    prompt = f"""You are an expert software engineer. Generate a unified diff patch to fix a GitHub issue.

Issue title: {state['issue_title']}
Issue body:  {state['issue_body']}
{f"Issue comments:{chr(10)}{comments_text}" if comments_text else ""}

Fix plan:
{state['plan']}

Current file contents:
{files_text}

Return ONLY the raw unified diff (git diff format).
Lines with changes start with --- (original) and +++ (new file), then @@ hunks.
Do NOT wrap in markdown code fences. Do NOT add explanation."""

    response = await _client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    patch = response.text.strip()

    # Strip markdown fences if the model adds them anyway
    if patch.startswith("```"):
        lines = patch.split("\n")
        end = -1 if lines[-1].startswith("```") else len(lines)
        patch = "\n".join(lines[1:end])

    return {"patch": patch}