#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
class NotCompletedError(Exception):
    ...


class ScriptWithError(Exception):

    def __init__(self, message: str = None, command=None):
        self.message = message
        self.command = command


class NotFoundEdgeError(ValueError):
    ...
