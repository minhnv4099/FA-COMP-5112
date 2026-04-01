#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import json
from abc import ABC
from typing import Any, Literal, Callable, Type, Optional, cast
from typing_extensions import Annotated, Unpack
from pydantic import BaseModel
from pydantic import ConfigDict
from langchain_core.tools.base import BaseTool as LangchainBaseTool
from langchain_core.runnables import Runnable
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig, Decision, DecisionType
from langchain.agents.middleware.types import ModelRequest
from langchain.tools import tool


class SchemaAnnotationError(TypeError):
    """Raised when ``args_schema`` is missing or has an incorrect type annotation"""


class ToolExecutionException(Exception):
    """Exception thrown when a tool execution error occurs.

    This exception allows tools to signal errors without stopping the agent.
    The error is handled according to the tool's ``handle_tool_error`` setting,
    and the result is returned as an observation to the agent.
    """


TypeBaseModel = Type[BaseModel]
ArgsSchema = TypeBaseModel | dict[str, Any]
ALLOWED_DECISIONS = ["approve", "edit", "reject"]


class ToolWithInterruptAction(LangchainBaseTool, ABC):
    """Base class for all LangWork tools.

    This abstract class defines the interface that all LangWork tools must implement.

    Tools are components that can be called by agents to perform specific actions.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate the tool class definition during subclass creation.

        Raises:
            SchemaAnnotationError: If ``args_schema`` has incorrect type annotation.
        """
        super().__init_subclass__(**kwargs)
        allowed_decisions = cls.__annotations__.get("allowed_decisions", None)

    def __init__(
        self,
        *args,
        allowed_decisions: Optional[list[DecisionType]] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        if kwargs.get('name'):
            self.name = kwargs["name"]

        if isinstance(allowed_decisions, bool):
            if allowed_decisions is True:
                allowed_decisions = ["approve", "edit", "reject"]
        elif isinstance(allowed_decisions, list):
            allowed_decisions = [decision for decision in allowed_decisions if decision in ALLOWED_DECISIONS]

        self.allowed_decisions = InterruptOnConfig(allowed_decisions=allowed_decisions)


def tool_with_interrupt(
    *args: Any,
    description: str | None = None,
    return_direct: bool = False,
    args_schema: ArgsSchema | None = None,
    infer_schema: bool = True,
    response_format: Literal["content", "content_and_artifact"] = "content",
    parse_docstring: bool = False,
    error_on_invalid_docstring: bool = True,
    human_confirm: bool | list[Literal['approve', 'edit', 'reject']] = False,
) -> LangchainBaseTool | Callable[[Callable | Runnable], LangchainBaseTool]:
    """Decorate upper `@tool` to define allowed decision for interrupting when defining langchain tool."""

    if isinstance(human_confirm, bool):
        allowed_decisions = human_confirm
    else:
        allowed_decisions = list(sorted(set(ALLOWED_DECISIONS).intersection(set(human_confirm)), reverse=False))
        if not allowed_decisions:
            allowed_decisions = False

    allowed_decisions = {"allowed_decisions": allowed_decisions}
    if parse_docstring:
        error_on_invalid_docstring = False

    def _create_tool_factory(name_or_callable: str | Callable | None = None, runnable: Runnable | None = None,):
        if callable(name_or_callable):
            _description = description or name_or_callable.__doc__
            _description = _description + json.dumps(allowed_decisions)
        elif runnable:
            _description = json.dumps(allowed_decisions)
        else:
            _description = description

        _tool = tool(
            name_or_callable,
            runnable,
            description=_description,
            return_direct=return_direct,
            args_schema=args_schema,
            infer_schema=infer_schema,
            response_format=response_format,
            parse_docstring=parse_docstring,
            error_on_invalid_docstring=error_on_invalid_docstring,
        )

        return _tool

    if args:
        if callable(args[0]):
            return _create_tool_factory(*args)

    return _create_tool_factory
