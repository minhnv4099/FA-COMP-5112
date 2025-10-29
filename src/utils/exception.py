#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#

__all__ = [
    "NotCompletedError",
    "ScriptWithError",
    "BreakGraphOperation",
    "NoRenderImages",
    "ExceedFixErrorAttempts",
    "NotSupportUserRefinement",
    "NoConnectionEdges",
]


class NoConnectionEdges(Exception):
    ...


class NotCompletedError(Exception):
    ...


class ScriptWithError(Exception):
    def __init__(self, message: str = None, command=None):
        self.message = message
        self.command = command


class BreakGraphOperation(Exception):
    def __init__(self, msg, state):
        self.state = state
        self.msg = msg


class NoRenderImages(BreakGraphOperation):
    ...


class ExceedFixErrorAttempts(BreakGraphOperation):
    ...


class NotSupportUserRefinement(BreakGraphOperation):
    ...


class UserTerminated(BreakGraphOperation):
    ...
