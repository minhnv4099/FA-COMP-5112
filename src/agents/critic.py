#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import glob
import logging
import os
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langgraph.config import RunnableConfig
from typing_extensions import override

from ..base.agent import AgentAsNode, register
from ..base.utils import DirectionRouter, Command, Send
from ..utils import DEFAULT_CAMERA_SETTING_FILE, ANCHOR_FILE, SAVE_CRITIC_DIR
from ..utils import InputT, OutputT
from ..utils import write_script, execute

logger = logging.getLogger(__name__)


@register(type="agent", name='critic')
class CriticAgent(AgentAsNode, name='Critic'):
    """
    The Critic Agent class
    """

    def __init__(
            self,
            metadata: dict = None,
            input_schema: InputT | dict = None,
            edges: dict[str, tuple[str]] = None,
            tool_schemas: list | list[dict] = None,
            output_schema: OutputT | list[OutputT] | list[dict] = None,
            model_name: str = None,
            model_provider: str = None,
            model_api_key: str = None,
            output_schema_as_tool: bool = None,
            chat_model: BaseChatModel = None,
            save_rendered_dir: str = None,
            anchor_script_path: str = None,
            validating_prompt: str = None,
            template_file: str = None,
            camera_setting_file: str = None,
            **kwargs
    ):
        super().__init__(
            metadata=metadata,
            input_schema=input_schema,
            edges=edges,
            tool_schemas=tool_schemas,
            output_schema=output_schema,
            model_name=model_name,
            model_provider=model_provider,
            model_api_key=model_api_key,
            output_schema_as_tool=output_schema_as_tool,
            chat_model=chat_model,
            template_file=template_file,
            **kwargs
        )

        super()._prepare_chat_template()
        self.validating_prompt = validating_prompt
        self.combined_script_template = "{creation_script}\n\n{additional_script}"

        self.camera_setting_file = camera_setting_file if camera_setting_file else DEFAULT_CAMERA_SETTING_FILE
        self.anchor_script_path = anchor_script_path if anchor_script_path else ANCHOR_FILE
        self.save_rendered_dir = save_rendered_dir if save_rendered_dir else SAVE_CRITIC_DIR

        os.makedirs(save_rendered_dir, exist_ok=True)
        os.makedirs(Path(anchor_script_path).parent, exist_ok=True)

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Command | Send | dict:
        script = state['current_script']
        ready_render_script = self._process_script(script)

        rendered_image_paths = self._run_to_get_rendered_images(ready_render_script)[0:2]

        critics_fixes = dict()
        fixes = []
        for i, image in enumerate(rendered_image_paths):
            # -----------------------------------------------
            formatted_prompt = self.chat_template.invoke({
                'image': image,
                'validating_prompt': self.validating_prompt,
            })
            response = self.anchor_call(formatted_prompt)
            # -----------------------------------------------
            critics_fixes[i] = response
            fixes.extend([d['fix'] for d in response])

        # ----------process critic-fixe list-----------
        #
        # ---------------------------------------------

        update_state = {
            'queries': fixes,
            'coding_task': 'improve',
            'is_sub_call': False,
            'caller': 'critic',
            'has_docs': False,
            'critics_fixes': critics_fixes,
            'rendered_images': rendered_image_paths,
        }

        return DirectionRouter.goto(state=update_state, node='coding', method='command')

    def check_critic_fixes(self, critic_fixes: list[dict]):
        raise NotImplementedError

    def _run_to_get_rendered_images(self, script: str):
        write_script(script, self.anchor_script_path)
        execute(script_path=self.anchor_script_path)

        rendered_image_paths = glob.glob(fr"{self.save_rendered_dir}/*.png")
        rendered_image_paths.sort()

        return rendered_image_paths

    def _process_script(self, script):
        with open(self.camera_setting_file, mode='r') as f:
            camera_script = f.read()
        camera_script = camera_script.replace("{save_dir}", self.save_rendered_dir)

        combined_script = self.combined_script_template.format(
            creation_script=script,
            additional_script=camera_script,
        )

        return combined_script

    @override
    def anchor_call(self, formatted_prompt: str, *args, **kwargs):
        return [
            {
                'critic': 'The armrests aren\'t attached to the seat',
                'fix': 'Move armrests down by y-axis'
            },
            {
                'critic': 'The legs are too long',
                'fix': 'Decrease length of legs'
            }
        ]

    @override
    def chat_model_call(self, formatted_prompt: str, *args, **kwargs):
        raise NotImplementedError
