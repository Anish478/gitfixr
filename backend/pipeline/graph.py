# TODO: LangGraph StateGraph definition
# Wires all agents together:
#   memory_retrieval → code_reader → planner → code_writer → sandbox → critic
#   critic: retry → code_writer | pass → pr_opener | give_up → memory_storage
