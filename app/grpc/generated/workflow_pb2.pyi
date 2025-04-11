from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ExecutionStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STATUS_UNSPECIFIED: _ClassVar[ExecutionStatus]
    PENDING: _ClassVar[ExecutionStatus]
    RUNNING: _ClassVar[ExecutionStatus]
    COMPLETED: _ClassVar[ExecutionStatus]
    FAILED: _ClassVar[ExecutionStatus]
    CANCELLED: _ClassVar[ExecutionStatus]
STATUS_UNSPECIFIED: ExecutionStatus
PENDING: ExecutionStatus
RUNNING: ExecutionStatus
COMPLETED: ExecutionStatus
FAILED: ExecutionStatus
CANCELLED: ExecutionStatus

class ExecuteWorkflowRequest(_message.Message):
    __slots__ = ("workflow_id",)
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    workflow_id: str
    def __init__(self, workflow_id: _Optional[str] = ...) -> None: ...

class WorkflowExecutionUpdate(_message.Message):
    __slots__ = ("execution_id", "workflow_id", "status", "current_task_id", "current_task_name", "message")
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CURRENT_TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CURRENT_TASK_NAME_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    current_task_id: str
    current_task_name: str
    message: str
    def __init__(self, execution_id: _Optional[str] = ..., workflow_id: _Optional[str] = ..., status: _Optional[_Union[ExecutionStatus, str]] = ..., current_task_id: _Optional[str] = ..., current_task_name: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...

class GetWorkflowStatusRequest(_message.Message):
    __slots__ = ("execution_id",)
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    execution_id: str
    def __init__(self, execution_id: _Optional[str] = ...) -> None: ...

class WorkflowStatusResponse(_message.Message):
    __slots__ = ("execution_id", "workflow_id", "status", "last_message")
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    WORKFLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    LAST_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    last_message: str
    def __init__(self, execution_id: _Optional[str] = ..., workflow_id: _Optional[str] = ..., status: _Optional[_Union[ExecutionStatus, str]] = ..., last_message: _Optional[str] = ...) -> None: ...
