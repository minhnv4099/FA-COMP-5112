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
from ..utils import load_image_content
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
            max_critics: int = None,
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

        self.max_critics = max_critics
        self._make_dirs()

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Command | Send | dict:
        start_message = "-" * 50 + self.name + "-" * 50
        logger.info(start_message)

        script = state['current_script']
        logger.info("Setup camera to capture images")
        ready_render_script, save_dir = self._process_script(script)

        rendered_image_paths = self._run_to_get_rendered_images(ready_render_script, save_dir)
        logger.info(f"Rendered images: {rendered_image_paths}")

        critics_fixes = dict()
        validating_prompt = state.get('validating_prompt', None) or self.validating_prompt
        logger.info(f"Validating prompt: {validating_prompt}")
        fixes = []
        messages = []
        for i, image in enumerate(rendered_image_paths):
            # -----------------------------------------------
            # logger.info(f"image ({i+1}/{len(rendered_image_paths)}: {image}")
            formatted_prompt = self.chat_template.invoke({
                'image': load_image_content(image),
                'validating_prompt': validating_prompt,
                'max_critics': self.max_critics,
            })
            response, query_messages = self.chat_model_call(formatted_prompt)
            if messages:
                messages.extend(query_messages[1:])
            else:
                messages.extend(query_messages)

            logger.info(f"image ({i + 1}/{len(rendered_image_paths)}): {image}: {len(response)} critics")
            # -----------------------------------------------
            critics_fixes[i] = response
            fixes.extend([d['fix'] for d in response])

        # logger.info(f'critics_fixes: {critics_fixes}')
        logger.info(f'fixes: {len(fixes)}')
        # ----------process critic-fixe list-----------
        #
        # ---------------------------------------------
        self._log_conversation(logger, messages)
        end_message = "*" * (100 + len(self.name))
        logger.info(end_message)

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

    def _run_to_get_rendered_images(self, script: str, save_dir):
        logger.info(f'Write rendered-ready script to "{self.anchor_script_path}"')
        write_script(script, self.anchor_script_path)
        execute(script_path=self.anchor_script_path)

        rendered_image_paths = glob.glob(fr"{save_dir}/*.png")
        rendered_image_paths.sort()

        return rendered_image_paths

    def _process_script(self, script):
        with open(self.camera_setting_file, mode='r') as f:
            camera_script = f.read()
        save_dir = f"{self.save_rendered_dir}/{len(os.listdir(self.save_rendered_dir))}"
        os.makedirs(save_dir, exist_ok=True)
        camera_script = camera_script.replace("{{save_dir}}", save_dir)

        combined_script = self.combined_script_template.format(
            creation_script=script,
            additional_script=camera_script,
        )

        return combined_script, save_dir

    def _make_dirs(self):
        par = Path(self.anchor_script_path).parent
        import shutil
        shutil.rmtree(self.save_rendered_dir, ignore_errors=True)

        os.makedirs(self.save_rendered_dir, exist_ok=True)
        os.makedirs(par, exist_ok=True)

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

    # @override
    # def chat_model_call(self, formatted_prompt: str, *args, **kwargs):
    #     ai_message = self.chat_model.invoke(formatted_prompt)
    #     return ai_message.tool_calls[-1]['args']['critic_fix_list']
