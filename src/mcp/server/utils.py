#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from typing import Any

logger = logging.getLogger(__name__)


def require_human_confirm(*, asking_prompt: str, kwargs: dict[str, Any]):
    """Require need of confirmation from human to proceed.

    Args:
        asking_prompt: Prompt exposed to human, containing all information about tool execution.
        kwargs: Contains only key ``user_confirm``: Confirm from human, `y` or others. If `y`, proceed tool execution.

    Raises:
        NeedHumanConfirmException: If need a confirmation from human along with asking prompt.
        HumanAbortedException: If human aborted tool executing along with a message.
    """
    if not kwargs or "user_confirm" not in kwargs:
        logger.info(f"Waiting human confirm ...")
        raise NeedHumanConfirmException({
            "need_user_confirm": True,
            "asking_prompt": asking_prompt
        })

    if kwargs and kwargs['user_confirm'] != 'y':
        logger.info("User aborted executing, pass over.")
        raise HumanAbortedException("User aborted executing, pass over.")


class HumanAbortedException(Exception):
    ...


class NeedHumanConfirmException(Exception):
    def __init__(self, kwargs: dict[str, Any]):
        self.kwargs = kwargs
