# TODO: Agent 4 — Sandbox (E2B)
# No LLM — uses E2B cloud containers
# Input:  patch, relevant_files
# Output: sandbox_result {tests_passed, test_output, security_issues, security_score}
# Steps:  spin up container → apply patch → run pytest → run bandit → destroy
