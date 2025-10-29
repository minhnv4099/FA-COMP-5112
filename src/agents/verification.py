#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import overload
from typing_extensions import override
from collections import defaultdict

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables.config import RunnableConfig
from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    ChatPromptTemplate
)

from .critic import CriticAgent
from ..base.agent import AgentAsNode, register
from ..base.utils import DirectionRouter
from ..utils import InputT, OutputT
from ..utils import NoRenderImages
from ..utils import load_image_content, load_prompt_template_file

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
    ):
        logger.info(self.opening_symbols)

        # script after attempts fixing critics
        current_script = state['current_script']
        logger.info("Setup camera to capture fixes images")
        processed_script, save_dir = self._process_script(current_script)

        rendered_images = state['rendered_images'][:1]
        logger.info(f"Images BEFORE: {rendered_images}")

        modified_rendered_images = self._run_to_get_rendered_images(processed_script, save_dir)[:1]
        logger.info(f"Images AFTER: {modified_rendered_images}")

        # because of some reasons, the current script cannot render images
        # No way to compare two respective images
        if not modified_rendered_images:
            raise NoRenderImages(
                f"No image rendered by Verification Agent. Let's try again with a new task",
                state=state
            )

        solutions, messages, critics_solutions = self._verify(state, rendered_images, modified_rendered_images)

        # if still have solutions
        if solutions:
            logger.info(f"Solutions by Verification: {solutions}")
            if self.verification_tries < self.verification_attempts:
                self.verification_tries += 1
                logger.info(f"verify: {self.verification_tries}(tries)/{self.verification_attempts}(attempts)")
                next_node = 'coding'
            else:
                # Exceed the number of attempts during a session call this agent
                logger.info("Exceed verification attempts")
                self.verification_tries = 0
                next_node = 'user'
        # no critic from critic agent or use need to be solved, i.e. all solutions/change are satisfied
        else:
            next_node = 'user'
            self.verification_tries = 0

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
            'messages': messages
        }

        logger.info(self.ending_symbols)
        self.log_conversation(logger, messages)

        return DirectionRouter.goto(state=update_state, node=next_node, method='command')

    def _verify(self, state, rendered_images, modified_rendered_images):
        # This point out that the verification agent has solved all issues
        # meaning that, when additional prompt is typed, there are no longer any critics.
        # Just in expectation
        if state.get('additional_prompt', None):
            # no critics solutions
            return *self._verify_prompt(state, rendered_images, modified_rendered_images), None
        if state['critics_solutions']:
            # The agent is still solving issues
            return self._verify_critic(state, rendered_images, modified_rendered_images)

        return None

    def _verify_critic(self, state, rendered_images, modified_rendered_images):
        chat_template = self.__prepare_chat_template(human_template=self.human_verify_critic_template)
        critics_solutions_dict = state['critics_solutions']
        logger.info(critics_solutions_dict)
        remaining_critic_satisfied_solution_dict = defaultdict(list)
        solutions = []
        messages = []

        logger.info("Verify critics and fixes")
        for i, (ri, mi) in enumerate(zip(rendered_images, modified_rendered_images)):
            # ri: rendered image
            # mi: modified rendered image
            logger.info(f"image ({i + 1}/{len(modified_rendered_images)}): '{ri}' vs '{mi}'")
            critics_solutions = critics_solutions_dict.get(i, None)
            if not critics_solutions:
                continue
            # -----------------------------------------------------------------
            formatted_prompt = chat_template.invoke({
                'image': load_image_content(ri),
                'modified_image': load_image_content(mi),
                'critics_solutions': critics_solutions,
            })
            response, query_messages = self.chat_model_call(formatted_prompt)
            # -----------------------------------------------
            for c in response:
                if not c['satisfied']:
                    remaining_critic_satisfied_solution_dict[i].append({
                        'critic': c['remaining_critic'],
                        'solution': c['solution']
                    })
                    # remaining_critic_satisfied_solution_list.extend(unsatisfied_critics)
                    solutions.append(c['solution'])
            # -----------------------------------------------
            to_log_messages = [
                *chat_template.invoke({
                    'image': ri,
                    'modified_image': mi,
                    'critics_solutions': critics_solutions,
                }).to_messages(),
                query_messages[-1]
            ]
            if messages:
                messages.extend(to_log_messages[1:])
            else:
                messages.extend(to_log_messages)

        logger.info(f"Unsatisfied critics: {len(solutions)}")

        return solutions, messages, remaining_critic_satisfied_solution_dict

    def _verify_prompt(self, state, rendered_images, modified_rendered_images):
        logger.info(f"Verify additional prompt: {state['additional_prompt']}")

        chat_template = self.__prepare_chat_template(human_template=self.human_verify_prompt_template)
        messages = []
        solutions = []

        for i, (ri, fi) in enumerate(zip(rendered_images, modified_rendered_images)):
            logger.info(f"image ({i + 1}/{len(modified_rendered_images)}): '{ri}' vs '{fi}'")
            formatted_prompt = chat_template.invoke({
                'image': load_image_content(ri),
                'modified_image': load_image_content(fi),
                'additional_prompt': [state['additional_prompt'], ],
            })
            response, query_messages = self.chat_model_call(formatted_prompt)
            if isinstance(response, list):
                response = response[0]
            if not response['satisfied']:
                solutions.append(response['solution'])

            to_log_messages = [
                *chat_template.invoke({
                    'image': ri,
                    'modified_image': fi,
                    'additional_prompt': state['additional_prompt']
                }).to_messages(),
                query_messages[-1]
            ]
            if messages:
                messages.extend(to_log_messages[1:])
            else:
                messages.extend(to_log_messages)

        return solutions, messages

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

    def __prepare_chat_template(self, human_template):
        return ChatPromptTemplate(
            messages=[self.system_template, human_template],
            template_format='f-string'
        )

    @override
    def _prepare_chat_template(self) -> None:
        ...

    @override
    def _get_output(self, ai_message) -> str:
        dict_output = ai_message.tool_calls[-1]['args']
        key = list(dict_output.keys())[0]
        return dict_output[key]
