#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import os
import glob
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Generic, cast, Literal
from typing_extensions import override

from src.registry import RegisterNode, RegisterAgent
from src.utils import DirectionRouter
from src.utils.constants import (
    DEFAULT_CAMERA_SETTING_FILE,
    DEFAULT_RENDER_IMAGE_FILE,
    SAVE_CRITIC_DIR,
    DEFAULT_CAMERA_TEMPLATE_FILE
)
from src.node.base import BaseNode
from src.utils.decorator import add_note_docstring
from src.types import StateT, ContextT, InputT, OutputT
from src.utils.exception import NoRenderImages
from src.utils.file import load_image_content
from src.utils.file import write_script, execute_file

if TYPE_CHECKING:
    from langgraph.config import RunnableConfig
    from langgraph.runtime import Runtime
    from langgraph.types import Command
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='critic')
@RegisterNode(module_path=__name__, name='critic')
class CriticAgent(
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name='Planner',
    use_model=True
):
    """The Critic Agent class"""

    def __init__(
        self,
        *args,
        save_rendered_dir: str = None,
        anchor_script_path: str = None,
        validating_prompt: str = None,
        camera_template_file: str = None,
        camera_setting_file: str = None,
        render_image_file: str = None,
        max_critics: int = None,
        n_rendered_images: Optional[int] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.validating_prompt = validating_prompt
        self.combined_script_template = "{creation}\n\n{camera_setting}\n\n{capture}"

        self.anchor_script_path = anchor_script_path
        self.camera_template_file = camera_template_file if camera_template_file else DEFAULT_CAMERA_TEMPLATE_FILE
        self.camera_setting_file = camera_setting_file if camera_setting_file else DEFAULT_CAMERA_SETTING_FILE
        self.render_image_file = render_image_file if render_image_file else DEFAULT_RENDER_IMAGE_FILE
        self.save_rendered_dir = save_rendered_dir if save_rendered_dir else SAVE_CRITIC_DIR
        self._make_dirs()

        self.max_critics = max_critics
        self.n_rendered_images = n_rendered_images

    @override
    def __call__(
        self,
        state: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Command:
        """"""
        logger.info(self.opening_symbols)
        self.persistent_on_invoke = True

        logger.info("Setup camera to capture images")
        ready_render_script, save_dir = self._process_script(state['current_script'])

        rendered_image_paths = self._run_to_get_rendered_images(ready_render_script, save_dir)[:self.n_rendered_images]
        if not rendered_image_paths:
            state['msg'] = f"No image rendered by Critic Agent. Let's try again with a new task."
            raise NoRenderImages(state=state)

        logger.info(f"Rendered images: {rendered_image_paths}")

        validating_prompt = state.get('validating_prompt', None) or self.validating_prompt
        logger.info(f"Validating prompt: {validating_prompt}")

        critics_solutions_dict = dict()
        solutions = []
        messages = []
        for i, image in enumerate(rendered_image_paths):
            # -----------------------------------------------
            prompt_value = self.chat_template.invoke(
                input={
                    'image': load_image_content(image),
                    'validating_prompt': validating_prompt,
                    'max_critics': self.max_critics,
                }
            )

            response = cast(
                "ParsedTollCallMessage",
                self.invoke(
                    input=prompt_value,
                    config=self.config
                )
            )

            # -----------------------------------------------
            agent_response = response.get_field()
            critics_solutions_dict[i] = agent_response
            solutions.extend([d['solution'] for d in agent_response if not d['satisfied']])

            logger.info(f"image ({i + 1}/{len(rendered_image_paths)}): {image} - 🟣 🟣 🟣 {len(agent_response)} critics 🟣 🟣 🟣")

            # display image paths in conversation instead of base64 content
            to_log_messages = [
                *self.chat_template.invoke({
                    'image': image,
                    'validating_prompt': validating_prompt,
                    'max_critics': self.max_critics,
                }).to_messages(),
            ]
            messages = self._extend_conversation(
                his_conversation=messages,
                messages=to_log_messages
            )

        logger.info(f"Solutions by Critic: {len(solutions)} -- {solutions}")

        next_node: Literal['coding', 'user', '__end__']
        if solutions:
            next_node = 'coding'
        else:
            next_node = '__end__'

        update_state = {
            'agent_response': solutions,
            'critics_solutions': critics_solutions_dict,
            'coding_task': 'improve',
            'caller': 'critic',
            'rendered_images': rendered_image_paths,
            'messages': messages
        }

        self._finish_session(logger)

        return DirectionRouter.jump(
            updates=update_state,
            jump_to=next_node,
            method='command'
        )

    def check_critics_solutions(self, critics_solutions: list[dict]):
        raise NotImplementedError

    def _process_script(self, script):
        with open(self.camera_setting_file, mode='r') as f:
            camera_setting = f.read()

        with open(self.render_image_file, mode='r') as f:
            capture = f.read()

        save_dir = f"{self.save_rendered_dir}/{len(os.listdir(self.save_rendered_dir))}"
        os.makedirs(save_dir, exist_ok=True)

        camera_setting = camera_setting.replace("{{camera_template_file}}", self.camera_template_file)
        camera_setting = camera_setting.replace("{{save_dir}}", save_dir)

        combined_script = self.combined_script_template.format(
            creation=script,
            camera_setting=camera_setting,
            capture=capture
        )

        return combined_script, save_dir

    def _run_to_get_rendered_images(self, script: str, save_dir):
        logger.info(f'Write rendered-ready script to "{self.anchor_script_path}"')
        write_script(script, self.anchor_script_path)

        logger.info(f"Executing '{self.anchor_script_path}' to capture images.")
        execute_file(script_path=self.anchor_script_path)

        rendered_image_paths = glob.glob(fr"{save_dir}/*.png")
        rendered_image_paths.sort()

        return rendered_image_paths

    def _make_dirs(self):
        par = Path(self.anchor_script_path).parent

        os.makedirs(par, exist_ok=True)
        os.makedirs(self.save_rendered_dir, exist_ok=True)
