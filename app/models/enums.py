import enum

class StatusEnum(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExecutionTypeEnum(str, enum.Enum):
    SYNC = "sync"
    ASYNC = "async"