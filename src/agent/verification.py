#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from collections import defaultdict
from typing import (
    Sequence,
    Optional,
    Union,
    cast,
    TYPE_CHECKING,
    Literal,
    TypeAlias,
    Type,
    Generic
)
from typing_extensions import override

from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    ChatPromptTemplate
)
from langchain_core.runnables.config import RunnableConfig
from langgraph.runtime import Runtime

from src.agent.critic import CriticAgent
from src.node.base import BaseNode
from src.utils import DirectionRouter
from src.registry import RegisterAgent, RegisterNode
from src.types import StateT, ContextT, InputT, OutputT
from src.utils.decorator import add_note_docstring
from src.utils.exception import NoRenderImages
from src.utils.file import load_image_content, load_prompt_template_file

if TYPE_CHECKING:
    from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
    from langgraph.types import Command
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)

CriticSolutionType: TypeAlias = Type[dict[int, list[dict[Literal['critic', 'solution'], str]]]]


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='verification')
@RegisterNode(module_path=__name__, name='verification')
class VerificationAgent(
    CriticAgent,
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name='Verification'
):
    """The Verification Agent class"""

    def __init__(
        self,
        *args,
        verification_attempts: int = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.verification_attempts = verification_attempts
        self.verification_tries: int = 0

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

        # script after fixing
        logger.info("Setup camera to capture fixes images")
        processed_script, save_dir = self._process_script(state['current_script'])

        rendered_images = state['rendered_images']
        modified_rendered_images = self._run_to_get_rendered_images(processed_script, save_dir)[:len(rendered_images)]

        logger.info(f"Images BEFORE: {rendered_images}")
        logger.info(f"Images AFTER: {modified_rendered_images}")

        # because of some reasons, the current script cannot render images
        # No way to compare two respective images, raise and break
        if not modified_rendered_images:
            state['msg'] = f"No image rendered by Verification Agent. Let's try again with a new task"
            raise NoRenderImages(state=state)

        solutions, critics_solutions, messages = self._verify(
            state=state,
            rendered_images=rendered_images,
            modified_rendered_images=modified_rendered_images
        )

        logger.info(f"Solutions by Verification: {len(solutions)} -- {solutions}")

        next_node: Literal['user', 'coding', '__end__']
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
        next_node = '__end__'
        update_state = {
            # used by Coding agent
            'agent_response': solutions,
            'coding_task': 'improve',
            'caller': 'verification',
            # Used by Verification Agent
            'critics_solutions': critics_solutions,
            # Used by User Agent to terminate and return final results
            'rendered_images': modified_rendered_images,
            'msg': state.get('msg', ''),
            'message': []
        }

        self._finish_session(logger)

        return DirectionRouter.jump(
            updates=update_state,
            jump_to=next_node,
            method='command'
        )

    def _verify(
        self,
        state: StateT,
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
        state: StateT,
        rendered_images: Sequence[str],
        modified_rendered_images: Sequence[str]
    ) -> (list[str], CriticSolutionType, Sequence[BaseMessage]):
        """"""
        logger.info("Verify critics and solutions")

        chat_template = self._prepare_chat_template(human_template=self.human_verify_critic_template)
        critics_solutions_dict = state['critics_solutions']
        new_critic_satisfied_solution_dict = defaultdict(list)
        solutions = []
        messages = []
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
            prompt_value = chat_template.invoke({
                'image': load_image_content(ri),
                'modified_image': load_image_content(mi),
                'critics_solutions': critics_solutions,
            })

            response = cast(
                "ParsedTollCallMessage",
                self.invoke(
                    input=prompt_value,
                    config=self.config
                )
            )

            agent_response = response.get_field(field='ss_list')
            for c in agent_response:
                if not c['satisfied']:
                    new_critic_satisfied_solution_dict[i].append({
                        'critic': c['new_critic'],
                        'solution': c['solution']
                    })
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
                response,
            ]
            messages = self._extend_conversation(
                his_conversation=messages,
                messages=to_log_messages
            )

        return solutions, new_critic_satisfied_solution_dict, messages

    def _verify_prompt(
        self,
        state: StateT,
        rendered_images: Sequence[str],
        modified_rendered_images: Sequence[str]
    ) -> (list[str], None, Sequence[BaseMessage]):
        """"""
        logger.info(f"Verify additional prompt: {state['additional_prompt']}")

        chat_template = self._prepare_chat_template(human_template=self.human_verify_prompt_template)
        solutions = []
        messages = []

        for i, (ri, fi) in enumerate(zip(rendered_images, modified_rendered_images)):
            logger.info(f"image ({i + 1}/{len(modified_rendered_images)}): '{ri}' vs '{fi}'")
            # -----------------------------------------------
            prompt_value = chat_template.invoke({
                'image': load_image_content(ri),
                'modified_image': load_image_content(fi),
                'additional_prompt': [state['additional_prompt'], ],
            })

            response = cast(
                'ParsedTollCallMessage',
                self.invoke(
                    input=prompt_value,
                    config=self.config
                )
            )

            agent_response = response.get_field('ss_list', default=dict())
            solutions = [d['solution'] for d in agent_response[0] if not d['satisfied']]

            to_log_messages = [
                *chat_template.invoke({
                    'image': ri,
                    'modified_image': fi,
                    'additional_prompt': state['additional_prompt']
                }).to_messages(),
            ]
            messages = self._extend_conversation(
                his_conversation=messages,
                messages=to_log_messages
            )

        return solutions, None, messages

    @override
    def _prepare_message_templates(self, *args, **kwargs):
        template_dict = load_prompt_template_file(self.template_file)

        self.system_template = SystemMessagePromptTemplate.from_template(
            template=template_dict.get('system_template', """"""),
            template_format='f-string'
        )
        self.human_verify_critic_template = HumanMessagePromptTemplate.from_template(
            template=template_dict.get('human_verify_critic_template', """"""),
            template_format="f-string"
        )
        self.human_verify_prompt_template = HumanMessagePromptTemplate.from_template(
            template=template_dict.get('human_verify_prompt_template', """"""),
            template_format='f-string',
        )

    @override
    def _prepare_chat_template(
        self,
        system_template: Optional[Union[SystemMessagePromptTemplate, SystemMessage]] = None,
        human_template: Optional[Union[HumanMessagePromptTemplate, HumanMessage]] = None
    ) -> Union[ChatPromptTemplate, None]:
        if system_template is None and human_template is None:
            return None

        return super()._prepare_chat_template(
            system_template=system_template,
            human_template=human_template
        )
