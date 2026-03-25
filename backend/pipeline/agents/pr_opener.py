import os
import re
from github import Github, GithubException
import unidiff
from pipeline.state import AgentState


async def pr_opener(state: AgentState) -> dict:
    """
    Agent 4 — PR Opener  (no LLM — uses GitHub API only)
    Input state keys used:  repo_owner, repo_name, issue_title, plan, patch, relevant_files
    Output key returned:    pr_url
    """
    g  = Github(os.environ["GITHUB_TOKEN"])
    me = g.get_user()

    # Get the upstream (original) repo object
    upstream = g.get_repo(f"{state['repo_owner']}/{state['repo_name']}")

    # Fork it. If you already have a fork, PyGithub returns the existing one.
    fork = me.create_fork(upstream)

    # Build a URL-safe branch name from the issue title
    slug = re.sub(r"[^a-z0-9-]", "-", state["issue_title"].lower()[:50])
    slug = re.sub(r"-+", "-", slug).strip("-")
    branch_name = f"gitfixr/{slug}"

    # Create the branch off the fork's default branch HEAD commit
    default_sha = fork.get_branch(fork.default_branch).commit.sha
    try:
        fork.create_git_ref(ref=f"refs/heads/{branch_name}", sha=default_sha)
    except GithubException:
        pass  # branch already exists from a previous attempt — reuse it

    # Build a lookup of relevant_files by path for quick access
    files_by_path = {f["path"]: f["content"] for f in state["relevant_files"]}

    # Parse the patch to find which files actually changed
    patchset = unidiff.PatchSet(state["patch"])

    for patched_file in patchset:
        path = patched_file.path.lstrip("b/")

        # Get original content from relevant_files, or fetch from GitHub if not there
        if path in files_by_path:
            original = files_by_path[path]
        else:
            try:
                import base64, httpx
                headers = {"Authorization": f"token {os.environ['GITHUB_TOKEN']}"}
                async with httpx.AsyncClient(timeout=20) as http:
                    r = await http.get(
                        f"https://api.github.com/repos/{state['repo_owner']}/{state['repo_name']}/contents/{path}",
                        headers=headers,
                    )
                    data = r.json()
                    original = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            except Exception:
                continue  # can't get the file, skip it

        new_content = _apply_patch(original, state["patch"], path)
        if new_content == original:
            continue  # patch didn't apply, skip

        try:
            existing = fork.get_contents(path, ref=branch_name)
            fork.update_file(
                path    = path,
                message = f"gitfixr: fix {path}",
                content = new_content,
                sha     = existing.sha,
                branch  = branch_name,
            )
        except GithubException:
            fork.create_file(
                path    = path,
                message = f"gitfixr: fix {path}",
                content = new_content,
                branch  = branch_name,
            )

    # Open the PR: fork:branch → upstream:default_branch
    body = (
        "Automated fix by [gitFixr](https://github.com/laharigandrapu/gitfixr).\n\n"
        "**Fix plan:**\n" + state["plan"]
    )
    try:
        pr = upstream.create_pull(
            title = f"[gitfixr] Fix: {state['issue_title']}",
            body  = body,
            head  = f"{me.login}:{branch_name}",
            base  = upstream.default_branch,
        )
    except GithubException:
        # PR already exists — find and return it
        existing_prs = upstream.get_pulls(head=f"{me.login}:{branch_name}", state="open")
        pr = next(iter(existing_prs), None)
        if pr is None:
            raise

    return {"pr_url": pr.html_url}


def _apply_patch(original: str, patch: str, file_path: str) -> str:
    """
    Applies a unified diff to a single file's original content.

    How it works:
    - unidiff parses the diff into hunks (blocks of added/removed lines)
    - We walk the original file line by line, skipping removed lines and
      inserting added lines at the right positions
    - Returns the reconstructed file content as a string
    """
    try:
        patchset = unidiff.PatchSet(patch)
        for patched_file in patchset:
            # unidiff stores target path as "b/path" — strip the prefix
            x = patched_file.path.lstrip("b/")
            if x != file_path and patched_file.path != file_path:
                continue   # this file isn't in the patch

            original_lines = original.splitlines(keepends=True)
            result = []
            i = 0  # cursor into original_lines (0-indexed)

            for hunk in patched_file:
                # Copy unchanged lines before this hunk begins
                hunk_start = hunk.source_start - 1  # hunks are 1-indexed
                result.extend(original_lines[i:hunk_start])
                i = hunk_start

                for line in hunk:
                    if line.is_added:
                        result.append(line.value)      # insert new line
                    elif line.is_removed:
                        i += 1                         # skip old line
                    else:
                        result.append(original_lines[i])  # keep context line
                        i += 1

            # Copy any lines after the last hunk
            result.extend(original_lines[i:])
            return "".join(result)

    except Exception as exc:
        print(f"[gitFixr] Patch apply failed for {file_path}: {exc}")

    return original  # fallback: return file unchanged (no-op commit)