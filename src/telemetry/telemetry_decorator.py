#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
"""
Telemetry decorator for MCP tools.
"""
import logging
import time
import inspect
import functools
from typing import Callable, Any, Optional, Literal

from .telemetry import record_tool_usage, record_prompt_get, record_resource_read
logger = logging.getLogger("telemetry-decorator")


def telemetry_mcp_tool(tool_name: Optional[str]):
    return telemetry_tool(tool_source="mcp", tool_name=tool_name)


def telemetry_langchain_tool(tool_name: Optional[str]):
    return telemetry_tool(tool_source="langchain", tool_name=tool_name)


def telemetry_tool(tool_source: Literal['langchain', 'mcp'], tool_name: Optional[str]):
    """Decorator to add telemetry tracking MCP tools.
    Besides the result, computing duration and error also are included.
    """
    def decorator(func: Callable[..., Any]) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False
            error = None

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as exec_error:
                error = str(exec_error)
                raise
            finally:
                elapsed_ms = (time.time() - start_time)
                try:
                    record_tool_usage(
                        tool_source=tool_source,
                        tool_name=tool_name,
                        success=success,
                        elapsed_ms=elapsed_ms,
                        error=error
                    )
                except Exception as record_error:
                    logger.debug(f"Error recording tool telemetry: {record_error!r}")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False
            error = None

            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as exec_error:
                error = str(exec_error)
                raise
            finally:
                elapsed_ms = (time.time() - start_time)
                try:
                    record_tool_usage(
                        tool_source=tool_source,
                        tool_name=tool_name,
                        success=success,
                        elapsed_ms=elapsed_ms,
                        error=error
                    )
                except Exception as record_error:
                    logger.debug(f"Error recording tool telemetry: {record_error!r}")

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def telemetry_prompt(prompt_name: str):
    """Decorator to add telemetry tracking MCP tools.
    Besides the result, computing duration and error also are included.
    """
    def decorator(func: Callable[..., Any]) -> Callable:
        # wrap this to keep docs and args of 'func'
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False
            error = None
            prompt_text = ""

            try:
                prompt_text = func(*args, **kwargs)
                success = True
                return prompt_text
            except Exception as exec_error:
                error = str(exec_error)
                raise
            finally:
                elapsed_ms = (time.time() - start_time)
                try:
                    record_prompt_get(prompt_name, prompt_text, success, elapsed_ms, error)
                except Exception as record_error:
                    logger.debug(f"Error recording prompt telemetry: {record_error!r}")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False
            error = None
            prompt_text = ""

            try:
                result = await func(*args, **kwargs)
                prompt_text = result
                success = True
                return result
            except Exception as exec_error:
                error = str(exec_error)
                raise
            finally:
                elapsed_ms = (time.time() - start_time)
                try:
                    record_prompt_get(prompt_name, prompt_text, success, elapsed_ms, error)
                except Exception as record_error:
                    logger.debug(f"Error recording prompt telemetry: {record_error!r}")

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def telemetry_resource(resource_uri: str):
    """Decorator to add telemetry tracking MCP tools.
    Besides the result, computing duration and error also are included.
    """

    def decorator(func: Callable[..., Any]) -> Callable:
        # wrap this to keep docs and args of 'func'
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False
            error = None

            try:
                resource_content = func(*args, **kwargs)
                success = True
                return resource_content
            except Exception as exec_error:
                error = str(exec_error)
                raise
            finally:
                elapsed_ms = (time.time() - start_time)
                try:
                    record_resource_read(resource_uri, success, elapsed_ms, error)
                except Exception as record_error:
                    logger.debug(f"Error recording resource telemetry: {record_error!r}")

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False
            error = None

            try:
                resource_content = await func(*args, **kwargs)
                success = True
                return resource_content
            except Exception as exec_error:
                error = str(exec_error)
                raise
            finally:
                elapsed_ms = (time.time() - start_time)
                try:
                    record_resource_read(resource_uri, success, elapsed_ms, error)
                except Exception as record_error:
                    logger.debug(f"Error recording resource telemetry: {record_error!r}")

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
