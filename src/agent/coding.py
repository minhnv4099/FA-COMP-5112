#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import os
import logging
from copy import deepcopy
from typing import Union, Generic, Optional, cast, TYPE_CHECKING, Literal
from typing_extensions import override

from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.node import BaseNode
from src.registry import RegisterAgent, RegisterNode
from src.typing import StateT, ContextT, InputT, OutputT
from src.tools.comp_5112 import execute_script, write_script
from src.utils import DirectionRouter
from src.utils.decorator import add_note_docstring
from src.utils.exception import ScriptWithError, ExceedFixErrorAttempts
from src.utils.file import load_prompt_template_file

if TYPE_CHECKING:
    from langchain_core.prompt_values import PromptValue
    from langchain_core.messages import SystemMessage, HumanMessage
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module=__name__, name='coding')
@RegisterNode(module=__name__, name='coding')
class CodingAgent(
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name='Coding',
    use_model=True
):
    """The Coding Agent class"""

    @override
    def __init__(
        self,
        *args,
        save_scripts: bool = None,
        script_folder: str = None,
        anchor_script_file: str = None,
        check_error_file: str = None,
        fix_error_attempts: int = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.save_scripts = save_scripts

        self.check_error_file = check_error_file
        self.script_folder = script_folder
        self.anchor_script_file = anchor_script_file

        os.makedirs(self.script_folder, exist_ok=True)
        os.makedirs(os.path.split(self.anchor_script_file)[0], exist_ok=True)

        self.fix_error_attempts = fix_error_attempts
        self.fix_error_tries = 0

        self.copy_state = dict()

    @override
    def __call__(
        self,
        state: StateT,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Command[Literal['retriever', 'critic', 'verification']]:
        """"""
        logger.info(self.opening_symbols)
        self.persistent_on_invoke = True
        # This block is always executed only one time
        # store state from the official call (either to 'improve' or to 'generate')
        if not self.copy_state:
            logger.info(f"Copy state call from '{state['caller']}'")
            logger.info(f'Number of subtasks: {len(state["agent_response"])}')
            self.copy_state = deepcopy(state)
            self.copy_state['num_queries'] = len(state['agent_response'])
            self.copy_state['query_offset'] = 0
            self.copy_state['previous_scripts'] = []
            self.get_retrieved_docs = False

        try:
            formatted_prompt = self._prepare_prompt(state)
            script = self._generate(formatted_prompt)
        except ScriptWithError as e:
            logger.info('‼️ ‼️ ‼️ ‼️ ‼️ ‼️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️️ Catch error. Call Retriever ⚠️ ⚠️ ⚠️ ⚠️ ⚠️️ ‼️ ‼️ ‼️ ‼️ ‼️ ‼️')
            self.fix_error_tries += 1

            # Stop graph when over attempts fix error
            if self.fix_error_tries > self.fix_error_attempts:
                logger.info(f"Number of tries to fix error exceed allowed attempts ({self.fix_error_attempts})")
                state['msg'] = f'Cannot fix error after {self.fix_error_attempts}. Try again',
                raise ExceedFixErrorAttempts(state=state)

            """Recall Coding Agent if catch command when executing script
            Before fix code, call Retriever Agent to get relevant documents
            `e.command` is a command call retriever with command and command script.
            """
            self._finish_session(_logger=logger)
            return e.command

        # ------------------ error-free --------------------
        # the generated script is error-free, an ending point of recursive calls
        self.copy_state['current_script'] = script
        self.copy_state['previous_scripts'].append(script)
        self.copy_state['query_offset'] += 1
        self.copy_state['messages'] = self.get_messages(self.config)

        # reset fix error tries after each query
        self.fix_error_tries = 0
        updates = self.copy_state
        next_node: Literal[
            'coding',
            'retriever',
            'critic',
            'verification',
        ]
        # continue with the next query and send it to coding
        if self.copy_state['query_offset'] < self.copy_state['num_queries']:
            # Continue with the next query
            logger.info("✅ ✅ ✅ ✅ ✅ ✅ ⏭️ ⏭️ ⏭️ ⏭️ ⏭️ ⏭️ Continue with next query ⏭️ ⏭️ ⏭️ ⏭️ ⏭️ ⏭️ ✅ ✅ ✅ ✅ ✅ ✅")
            next_node = 'coding'
        else:
            logger.info(f"Write the latest script to '{self.anchor_script_file}'")
            # call a toll to write script
            write_script.invoke({
                'script': self.copy_state['current_script'],
                'file_path': self.anchor_script_file,
            })
            # save all generated scripts
            save_all_scripts(
                save_folder=self.script_folder,
                scripts=self.copy_state['previous_scripts'],
                caller=self.copy_state['caller']
            )

            # identify the next node based on the caller (i.e. previous node), only base on original call.
            next_node = 'critic'   # default when 'caller' == 'planner'
            if self.copy_state['caller'] in ('critic', 'verification', 'user'):
                next_node = 'verification'

            # save final response
            updates['agent_response'] = updates['current_script']
            updates['messages'] = self.get_messages()
            # reset copy state
            self.copy_state = dict()
            logger.info("✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ Finish a call, move to next node ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅")

        logger.info(f'coding -> {next_node}')
        self._finish_session(_logger=logger)

        # return stored original state ('copy_state' instead of 'state')
        # as there may be some sub calls from `retriever` that may change state.
        return DirectionRouter.jump(
            updates=updates,
            jump_to=next_node,
            method='command'
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

    @override
    def _prepare_message_templates(self, *args, **kwargs):
        template_dict = load_prompt_template_file(self.template_file)

        self.system_template = SystemMessagePromptTemplate.from_template(
            template=template_dict['system_template'],
            template_format='f-string'
        )
        self.human_generate_template = HumanMessagePromptTemplate.from_template(
            template=template_dict['human_generate_template'],
            template_format="f-string"
        )
        self.human_fix_template = HumanMessagePromptTemplate.from_template(
            template=template_dict['human_fix_template'],
            template_format='f-string',
        )
        self.human_improve_template = HumanMessagePromptTemplate.from_template(
            template=template_dict['human_improve_template'],
            template_format="f-string",
        )

    def _prepare_prompt(self, state: Union[dict, StateT]) -> PromptValue:
        """Prepare prompt template base on task

        Args:
            state: state of the call
        """
        if state['coding_task'] == 'generate':
            formatted_prompt = self._prepare_generate_prompt(state)
        elif state['coding_task'] == "improve":
            assert 'current_script' in state
            formatted_prompt = self._prepare_improve_prompt(state)
        else:
            assert 'current_script' in state
            formatted_prompt = self._prepare_fix_prompt(state)

        return formatted_prompt

    def _prepare_generate_prompt(self, state):
        chat_template = self._prepare_chat_template(human_template=self.human_generate_template)

        # that's called only when coding_task is 'generate'
        query_and_instruction = state['agent_response'][self.copy_state['query_offset']]
        query = query_and_instruction['query']
        instruction = query_and_instruction['instruction']

        logger.info(
            f"{state['coding_task']}: query {1 + self.copy_state['query_offset']}/{self.copy_state['num_queries']}: {query}")
        logger.info(f"Number of previous scripts: {len(self.copy_state['previous_scripts'])}")
        # ---------------------------------------------------
        formatted_prompt = chat_template.invoke(
            input={
                "task": query,
                "previous_scripts": dump_scripts(self.copy_state['previous_scripts']),
                "instruction": instruction
            }
        )
        # ---------------------------------------------------
        return formatted_prompt

    def _prepare_fix_prompt(self, state):
        chat_template = self._prepare_chat_template(human_template=self.human_fix_template)

        logger.info(f"{state['coding_task']}: {self.fix_error_tries}(tries)/{self.fix_error_attempts}(attempts)")
        # logger.info(f"error: {state['agent_response'][0]['query']}")

        query_and_instruction = state['agent_response'][0]
        error = query_and_instruction['query']
        instruction = query_and_instruction['instruction']
        # ---------------------------------------------------
        formatted_prompt = chat_template.invoke(
            input={
                'current_script': state['current_script'],
                'error': error,
                'instruction': instruction
            }
        )
        # ---------------------------------------------------
        return formatted_prompt

    def _prepare_improve_prompt(self, state):
        chat_template = self._prepare_chat_template(human_template=self.human_improve_template)
        solution = state['agent_response'][self.copy_state['query_offset']]

        logger.info(
            f"{state['coding_task']}: solution {1 + self.copy_state['query_offset']}/{self.copy_state['num_queries']}: {solution}")
        # ---------------------------------------------------
        formatted_prompt = chat_template.invoke(
            input={
                'current_script': state['current_script'],
                'solution': solution,
            }
        )
        # ---------------------------------------------------
        return formatted_prompt

    def _generate(self, formatted_prompt: PromptValue):
        while True:
            # ---------------------------Actual generation------------------------------
            response = cast(
                "ParsedTollCallMessage",
                self.invoke(
                    input=formatted_prompt,
                    config=self.config
                )
            )

            script = response.get_field('script', '')
            # call tool to write the script
            write_script.invoke({
                "script": script,
                "file_path": self.check_error_file
            })

            # call tool to execute the script
            logger.info('Executing to check error')
            stdout = execute_script.invoke(input={'script_path': self.check_error_file})

            # no error yielded
            if 'no error' in stdout.lower():
                logger.info(stdout)
                return script
            else:
                # raise the call to 'retriever' agent to fix error
                raise ScriptWithError(command=DirectionRouter.jump(
                    updates={
                        'current_script': script,
                        'coding_task': 'fix',
                        'agent_response': [stdout, ],
                        'messages': []
                    },
                    jump_to='retriever', method='command'
                ))


def dump_scripts(scripts: list[str]):
    if not scripts:
        return []
    script_string = '=' * 150
    for script in scripts:
        script_string += "\n```python\n"
        script_string += script
        script_string += "\n```\n"
        script_string += '=' * 150 + '\n'

    return script_string


def save_all_scripts(
    save_folder: str,
    scripts: list[str],
    caller: str
):
    caller_folder = os.path.join(save_folder, caller)
    os.makedirs(caller_folder, exist_ok=True)

    n = len(os.listdir(caller_folder))
    save_dir = os.path.join(caller_folder, str(n))
    os.makedirs(save_dir, exist_ok=True)

    for i, script in enumerate(scripts):
        file = os.path.join(save_dir, f"script_{i}.py")
        write_script.invoke({
            'script': script,
            'file_path': file,
        })

    logger.info(f'Write all generated scripts to folder "{save_dir}"')
