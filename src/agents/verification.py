#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables.config import RunnableConfig
from typing_extensions import override

from src import OutputT
from src.agents.critic import CriticAgent
from src.base.agent import AgentAsNode, register
from src.base.typing import InputT
from src.base.utils import DirectionRouter

logger = logging.getLogger(__name__)


@register(type="agent", name='verification')
class VerificationAgent(CriticAgent, AgentAsNode, name='Verification'):
    """
    The Verification Agent class
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
            verification_attempts: int = None,
            **kwargs
    ):
        super().__init__(
            metadata,
            input_schema,
            edges,
            tool_schemas,
            output_schema,
            model_name,
            model_provider,
            model_api_key,
            output_schema_as_tool,
            chat_model,
            save_rendered_dir,
            anchor_script_path,
            validating_prompt,
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
        current_script = state['current_script']
        processed_script = self._process_script(current_script)

        fixed_rendered_images = self._run_to_get_rendered_images(processed_script)[0:1]
        rendered_images = state['rendered_images']

        critics_fixes = state['critics_fixes']

        critic_satisfied_solution = []
        # ri: rendered image
        # fi: fixed rendered image

        for i, (ri, fi) in enumerate(zip(rendered_images, fixed_rendered_images)):
            formatted_prompt = self._prepare_chat_prompt(
                image=ri, fixed_image=fi,
                critics_fixes=critics_fixes[i],
            )
            response = self.anchor_call(
                formatted_prompt,
                critics_fixes=critics_fixes[i]
            )

            critic_satisfied_solution.extend(response)

        unsatisfied_critics = list(filter(
            lambda d: d['satisfied'].lower() != "yes",
            critic_satisfied_solution,
        ))

        fixes = [d['fix'] for d in unsatisfied_critics]
        if self.verification_tries < self.verification_attempts:
            self.verification_tries += 1
            next_node = 'coding'
        else:
            # while True:
            #     prompts = interrupt(value="Enter additional prompt: ")
            #
            #     print(f"New prompts from human: {prompts}")
            #
            #     if prompts.lower() in ('q', 'quit'):
            #         break
            next_node = 'user'
            self.verification_tries = 0
        # ----------process critic-fixe list-----------
        #
        # ---------------------------------------------

        update_state = {
            'queries': fixes,
            'coding_task': 'improve',
            'is_sub_call': False,
            'caller': 'verification',
            'has_docs': False
        }

        return DirectionRouter.go_next(
            method='command',
            state=update_state,
            node=next_node
        )

    @override
    def _prepare_chat_prompt(
            self,
            image: str,
            fixed_image: str,
            critics_fixes: list,
            *args,
            **kwargs
    ):
        return image

    @override
    def anchor_call(self, formatted_prompt: str, critics_fixes: list, *args, **kwargs):
        for i, d in enumerate(critics_fixes):
            if i % 2 == 0:
                d['satisfied'] = 'YES'
            else:
                d['satisfied'] = 'Partially, some details are not solved'

        return critics_fixes

    @override
    def chat_model_call(self, formatted_prompt: str, *args, **kwargs):
        raise NotImplementedError
