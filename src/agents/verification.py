#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from collections import defaultdict
from typing import Sequence, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    ChatPromptTemplate
)
from langchain_core.runnables.config import RunnableConfig
from typing_extensions import override

from .critic import CriticAgent
from ..base.agent import AgentAsNode, register
from ..base.utils import DirectionRouter
from ..utils.exception import NoRenderImages
from ..utils.file import load_image_content, load_prompt_template_file
from ..utils.types import InputT, OutputT

logger = logging.getLogger(__name__)


@register(type="agent", name='verification')
class VerificationAgent(CriticAgent, AgentAsNode, node_name='Verification'):
    """The Verification Agent class"""

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
            verification_attempts: int = None,
            camera_setting_file: str = None,
            camera_template_file: str = None,
            # templates
            template_file: str = None,
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
            save_rendered_dir=save_rendered_dir,
            anchor_script_path=anchor_script_path,
            camera_setting_file=camera_setting_file,
            camera_template_file=camera_template_file,
            **kwargs
        )

        self.verification_attempts = verification_attempts
        self.verification_tries: int = 0

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> OutputT:
        """"""
        logger.info(self.opening_symbols)

        # script after fixing
        current_script = state['current_script']
        logger.info("Setup camera to capture fixes images")
        processed_script, save_dir = self._process_script(current_script)

        rendered_images = state['rendered_images']

        modified_rendered_images = self._run_to_get_rendered_images(processed_script, save_dir)[:len(rendered_images)]
        logger.info(f"Images BEFORE: {rendered_images}")
        logger.info(f"Images AFTER: {modified_rendered_images}")

        # because of some reasons, the current script cannot render images
        # No way to compare two respective images, raise and break
        if not modified_rendered_images:
            state['msg'] = f"No image rendered by Verification Agent. Let's try again with a new task"
            raise NoRenderImages(state=state)

        solutions, messages, critics_solutions = self._verify(state, rendered_images, modified_rendered_images)

        logger.info(f"Solutions by Verification: {len(solutions)} -- {solutions}")
        if solutions:
            # if still have solutions
            if self.verification_tries < self.verification_attempts:
                self.verification_tries += 1
                logger.info(f"verify: {self.verification_tries}(tries)/{self.verification_attempts}(attempts)")
                next_node = 'coding'
            else:
                # Exceed the number of attempts during a session call this agent
                logger.info("Exceed verification attempts. Use the latest results.")
                state['msg'] = "Exceed verification attempts. Use the latest results."
                self.verification_tries = 0
                next_node = 'user'
        else:
            # no critic from critic agent or use need to be solved, i.e. all solutions/change are satisfied
            next_node = 'user'
            self.verification_tries = 0

        self._finish_session(logger, messages)

        update_state = {
            # used by Coding agent
            'queries': solutions,
            'coding_task': 'improve',
            'is_sub_call': False,
            'caller': 'verification',
            'has_docs': False,
            # Used by Verification Agent
            'critics_solutions': critics_solutions,
            # Used by User Agent to terminate and return final results
            'rendered_images': modified_rendered_images,
            'messages': messages,
            'msg': state.get('msg', '')
        }

        return DirectionRouter.goto(state=update_state, node=next_node, method='command')

    def _verify(
            self,
            state: InputT,
            rendered_images: Sequence[str],
            modified_rendered_images: Sequence[str]
    ) -> (list[str], Sequence, Optional[dict]):
        # This point out that the verification agent has solved all issues,
        # meaning that, when additional prompt is typed, there are no longer any critics.
        # Just in expectation
        if state.get('additional_prompt', None):
            # no critics solutions
            return self._verify_prompt(state, rendered_images, modified_rendered_images)
        if state['critics_solutions']:
            # The agent is still solving issues
            return self._verify_critic(state, rendered_images, modified_rendered_images)

        return None

    def _verify_critic(
            self,
            state,
            rendered_images,
            modified_rendered_images
    ) -> (list[str], Sequence, dict):
        """"""
        logger.info("Verify critics and fixes")

        chat_template = self._prepare_chat_template(human_template=self.human_verify_critic_template)
        critics_solutions_dict = state['critics_solutions']
        new_critic_satisfied_solution_dict = defaultdict(list)
        solutions = []
        conversation = []

        for i, (ri, mi) in enumerate(zip(rendered_images, modified_rendered_images)):
            # ri: rendered image
            # mi: modified rendered image
            logger.info(f"image ({i + 1}/{len(modified_rendered_images)}): '{ri}' vs '{mi}'")
            critics_solutions = critics_solutions_dict.get(i, None)
            if not critics_solutions:
                continue
            previous_critics = [d['critic'] for d in critics_solutions]
            previous_solutions = [d['solution'] for d in critics_solutions]
            # ---------------------------------------------------------------
            formatted_prompt = chat_template.invoke({
                'image': load_image_content(ri),
                'modified_image': load_image_content(mi),
                'critics_solutions': critics_solutions,
            })
            response, _messages = self.chat_model_call(formatted_prompt)
            # -----------------------------------------------
            for c in response:
                if not c['satisfied']:
                    new_critic_satisfied_solution_dict[i].append({
                        'critic': c['new_critic'],
                        'solution': c['solution']
                    })
                    # -----------------------------------------------
                    solutions.append(c['solution'])
                    logger.info(f'Same critic? {c["new_critic"] in previous_critics} & '
                                f'Same solution?: {c["solution"] in previous_solutions}')
            # -----------------------------------------------
            to_log_messages = [
                *chat_template.invoke({
                    'image': ri,
                    'modified_image': mi,
                    'critics_solutions': critics_solutions,
                }).to_messages(),
                _messages[-1]
            ]
            conversation = self._extend_conversation(his_conversation=conversation, messages=to_log_messages)

        return solutions, conversation, new_critic_satisfied_solution_dict

    def _verify_prompt(self, state, rendered_images, modified_rendered_images) \
            -> (list[str], Sequence, None):
        logger.info(f"Verify additional prompt: {state['additional_prompt']}")

        chat_template = self._prepare_chat_template(human_template=self.human_verify_prompt_template)
        conversation = []
        solutions = []

        for i, (ri, fi) in enumerate(zip(rendered_images, modified_rendered_images)):
            logger.info(f"image ({i + 1}/{len(modified_rendered_images)}): '{ri}' vs '{fi}'")
            # -----------------------------------------------
            formatted_prompt = chat_template.invoke({
                'image': load_image_content(ri),
                'modified_image': load_image_content(fi),
                'additional_prompt': [state['additional_prompt'], ],
            })
            response, _messages = self.chat_model_call(formatted_prompt)
            # -----------------------------------------------
            if isinstance(response, list):
                # expect only one (issue, solution) per image
                response = response[0]
            if not response['satisfied']:
                solutions.append(response['solution'])
            # -----------------------------------------------
            to_log_messages = [
                *chat_template.invoke({
                    'image': ri,
                    'modified_image': fi,
                    'additional_prompt': state['additional_prompt']
                }).to_messages(),
                _messages[-1]
            ]
            conversation = self._extend_conversation(his_conversation=conversation, messages=to_log_messages)

        return solutions, conversation, None

    @override
    def _prepare_message_templates(self, *args, **kwargs):
        template_dict = load_prompt_template_file(self.template_file)
        self.system_template = SystemMessagePromptTemplate.from_template(
            template=template_dict['system_template'],
            template_format='f-string'
        )
        self.human_verify_critic_template = HumanMessagePromptTemplate.from_template(
            template=template_dict['human_verify_critic_template'],
            template_format="f-string"
        )
        self.human_verify_prompt_template = HumanMessagePromptTemplate.from_template(
            template=template_dict['human_verify_prompt_template'],
            template_format='f-string',
        )

    def _prepare_chat_template(self, human_template=None):
        if human_template is None:
            return None
        return ChatPromptTemplate(
            messages=[self.system_template, human_template],
            template_format='f-string'
        )
