#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from pydantic import field_validator


class NeedReferenceDirMixin:

    def __init__(self, *args, reference_dir: str = '.', **kwargs):
        super().__init__(*args, **kwargs)

        self.reference_dir = reference_dir


class NeedAskHumanMixin:
    """The Mixin enforce need confirmation from human."""

    @field_validator("ask_human", mode="before")
    @classmethod
    def _validate_human_confirm(cls, v: bool) -> bool:
        """Validate commands."""
        return True
