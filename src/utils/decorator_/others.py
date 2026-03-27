#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
def must_override(func: callable):
    """The decorator indicating the ``func`` must be overrided in subclasses.

    If no needed, just simply call the super's method
    """

    func.__must_override__ = True
    return func


def add_note_docstring(docs):
    """Add additional note information to function and class.

    This action doesn't change anything other than **note**.
    """
    def _inner_add(symbol):
        symbol.__note_docstring__ = docs

        return symbol

    return _inner_add
