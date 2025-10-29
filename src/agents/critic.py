#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import glob
import logging
from pathlib import Path
from typing_extensions import override

from langchain_core.language_models import BaseChatModel
from langgraph.config import RunnableConfig

from ..base.agent import AgentAsNode, register
from ..base.utils import DirectionRouter, Command, Send
from ..utils import DEFAULT_CAMERA_SETTING_FILE, DEFAULT_CAPTURE_IMAGE_FILE, SAVE_CRITIC_DIR
from ..utils import InputT, OutputT
from ..utils import NoRenderImages
from ..utils import load_image_content
from ..utils import write_script, execute_file

logger = logging.getLogger(__name__)


@register(type="agent", name='critic')
class CriticAgent(AgentAsNode, node_name='Critic'):
    """The Critic Agent class"""

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
            capture_image_file: str = None,
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
        self._prepare_chat_template()
        self.validating_prompt = validating_prompt
        self.combined_script_template = "{creation}\n\n{camera_setting}\n\n{capture}"

        self.anchor_script_path = anchor_script_path
        self.camera_setting_file = camera_setting_file if camera_setting_file else DEFAULT_CAMERA_SETTING_FILE
        self.capture_image_file = capture_image_file if capture_image_file else DEFAULT_CAPTURE_IMAGE_FILE
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
        logger.info(self.opening_symbols)

        script = state['current_script']
        logger.info("Setup camera to capture images")
        ready_render_script, save_dir = self._process_script(script)

        rendered_image_paths = self._run_to_get_rendered_images(ready_render_script, save_dir)[:1]  # change index
        if not rendered_image_paths:
            raise NoRenderImages(
                f"No image rendered by Critic Agent. Let's try again with a new task.",
                state=state
            )
        logger.info(f"Rendered images: {rendered_image_paths}")

        validating_prompt = state.get('validating_prompt', None) or self.validating_prompt
        logger.info(f"Validating prompt: {validating_prompt}")

        critics_solutions_dict = dict()
        critics_solutions_list = []
        messages = []
        for i, image in enumerate(rendered_image_paths):
            # -----------------------------------------------
            formatted_prompt = self.chat_template.invoke({
                'image': load_image_content(image),
                'validating_prompt': validating_prompt,
                'max_critics': self.max_critics,
            })
            response, query_messages = self.chat_model_call(formatted_prompt)
            # -----------------------------------------------
            critics_solutions_dict[i] = response
            critics_solutions_list.extend(response)
            # -----------------------------------------------
            logger.info(f"image ({i + 1}/{len(rendered_image_paths)}): {image} - {len(response)} critics")
            # display path of image in conversation instead of base64 content
            to_log_messages = [
                *self.chat_template.invoke({
                    'image': image,
                    'validating_prompt': validating_prompt,
                    'max_critics': self.max_critics,
                }).to_messages(),
                query_messages[-1]
            ]
            if messages:
                # exclude the system message
                messages.extend(to_log_messages[1:])
            else:
                messages.extend(to_log_messages)

        logger.info(f'critics and solutions: {len(critics_solutions_list)}')
        solutions = [d['solution'] for d in critics_solutions_list]
        logger.info(f"Solutions by Critic: {solutions}")
        # ----------process critic-fixe list-----------
        #
        # ---------------------------------------------
        self.log_conversation(logger, messages)
        logger.info(self.ending_symbols)

        update_state = {
            'queries': solutions,
            'coding_task': 'improve',
            'is_sub_call': False,
            'caller': 'critic',
            'has_docs': False,
            'critics_solutions': critics_solutions_dict,
            'rendered_images': rendered_image_paths,
            'messages': messages
        }

        return DirectionRouter.goto(state=update_state, node='coding', method='command')

    def check_critic_fixes(self, critic_fixes: list[dict]):
        raise NotImplementedError

    def _process_script(self, script):
        with open(self.camera_setting_file, mode='r') as f:
            camera_setting = f.read()
        with open(self.capture_image_file, mode='r') as f:
            capture = f.read()

        save_dir = f"{self.save_rendered_dir}/{len(os.listdir(self.save_rendered_dir))}"
        os.makedirs(save_dir, exist_ok=True)
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
        execute_file(script_path=self.anchor_script_path)

        rendered_image_paths = glob.glob(fr"{save_dir}/*.png")
        rendered_image_paths.sort()

        return rendered_image_paths

    def _make_dirs(self):
        par = Path(self.anchor_script_path).parent
        # shutil.rmtree(self.save_rendered_dir, ignore_errors=True)

        os.makedirs(self.save_rendered_dir, exist_ok=True)
        os.makedirs(par, exist_ok=True)
