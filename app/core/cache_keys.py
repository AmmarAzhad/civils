import uuid

def workflow_cache_key(workflow_id: int | str) -> str:
    return f"workflow:{workflow_id}"

def execution_cache_key(execution_id: str | uuid.UUID) -> str:
    return f"execution:{execution_id}"