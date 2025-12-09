#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from abc import ABC
from typing import Any, Literal, Callable, Type
from typing_extensions import Annotated
from pydantic import BaseModel, Field, SkipValidation, ValidationError

from pydantic import ConfigDict
from langchain_core.tools.base import BaseTool as LangchainBaseTool


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


class BaseTool(LangchainBaseTool, ABC):
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

        args_schema_type = cls.__annotations__.get("args_schema", None)

        if args_schema_type is not None and args_schema_type == BaseModel:
            typehint_mandate = """
class ChildTool(BaseTool):
    ...
    args_schema: Type[BaseModel] = SchemaClass
    ..."""
            name = cls.__name__
            msg = (
                f"Tool definition for {name} must include valid type annotations"
                f" for argument 'args_schema' to behave as expected.\n"
                f"Expected annotation of 'Type[BaseModel]'"
                f" but got '{args_schema_type}'.\n"
                f"Expected class looks like:\n"
                f"{typehint_mandate}"
            )
            raise SchemaAnnotationError(msg)

    name: str
    """The unique name of the tool that clearly communicates its purpose."""
    description: str
    """Used to tell the model how/when/why to use the tool.
    
    You can provide few-shot examples as a part of the description.
    """
    args_schema: Annotated[ArgsSchema | None, SkipValidation()] = Field(
        default=None, description="The tool schema."
    )
    """Pydantic model class to validate and parse the tool's input arguments.
    
    Args schema should be:
    
    - A subclass of `pydantic.BaseModel`.
    """
    return_direct: bool = False
    """Whether to return the tool's output directly.

    Setting this to `True` means that after the tool is called, the `AgentExecutor` will
    stop looping.
    """
    verbose: bool = False
    """Whether to log the tool's progress."""
    tags: list[str] | None = None
    """Optional list of tags associated with the tool.

    These tags will be associated with each call to this tool,
    and passed as arguments to the handlers defined in `callbacks`.

    You can use these to, e.g., identify a specific instance of a tool with its use
    case.
    """
    metadata: dict[str, Any] | None = None
    """Optional metadata associated with the tool.

    This metadata will be associated with each call to this tool,
    and passed as arguments to the handlers defined in `callbacks`.

    You can use these to, e.g., identify a specific instance of a tool with its use
    case.
    """

    handle_tool_error: bool | str | Callable[[ToolExecutionException], str] | None = "Error when executing tool."
    """Handle the content of the `ToolException` thrown."""

    handle_validation_error: (
            bool | str | Callable[[ValidationError], str] | None
    ) = False
    """Handle the content of the `ValidationError` thrown."""

    response_format: Literal["content", "content_and_artifact"] = "content"
    """The tool response format.

    If `'content'` then the output of the tool is interpreted as the contents of a
    `ToolMessage`. If `'content_and_artifact'` then the output is expected to be a
    two-tuple corresponding to the `(content, artifact)` of a `ToolMessage`.
    """

    model_config = ConfigDict(extra='allow')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (
            "name" in kwargs
            and kwargs["name"] is not None
        ):
            self.name = kwargs["name"]
