#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
import os
from copy import deepcopy
from typing import Union

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langgraph.config import RunnableConfig
from langgraph.graph.state import END
from langgraph.types import Command, Send
from typing_extensions import override, Any

from ..base.agent import AgentAsNode
from ..base.mapping import register
from ..base.tool import execute_script, write_script
from ..base.utils import DirectionRouter
from ..utils.exception import ScriptWithError, ExceedFixErrorAttempts
from ..utils.file import load_prompt_template_file
from ..utils.types import InputT, OutputT

logger = logging.getLogger(__name__)


@register(type="agent", name='coding')
class CodingAgent(AgentAsNode, node_name='Coding', use_model=True):
    """The Coding Agent class"""

    @override
    def __init__(
            self,
            metadata: dict = None,
            edges: dict[str, tuple[str]] = None,
            input_schema: InputT = None,
            tool_schemas: list = None,
            output_schema: Any = None,
            output_schema_as_tool: bool = None,
            model_name: str = None,
            model_provider: str = None,
            model_api_key: str = None,
            chat_model: BaseChatModel = None,
            save_scripts: bool = None,
            script_folder: str = None,
            anchor_script_file: str = None,
            check_error_file: str = None,
            # templates
            template_file: str = None,
            fix_error_attempts: int = None,
            **kwargs
    ):
        super().__init__(
            metadata=metadata,
            edges=edges,
            input_schema=input_schema,
            tool_schemas=tool_schemas,
            output_schema=output_schema,
            output_schema_as_tool=output_schema_as_tool,
            model_name=model_name,
            model_provider=model_provider,
            model_api_key=model_api_key,
            chat_model=chat_model,
            template_file=template_file,
            **kwargs
        )
        self.save_scripts = save_scripts

        self.check_error_file = check_error_file
        self.script_folder = script_folder
        self.anchor_script_file = anchor_script_file
        # shutil.rmtree(self.script_folder, ignore_errors=True)
        os.makedirs(self.script_folder, exist_ok=True)
        os.makedirs(os.path.split(self.anchor_script_file)[0], exist_ok=True)

        self.fix_error_attempts = fix_error_attempts
        self.fix_error_tries = 0

        self.copy_state = dict()

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: RunnableConfig = None,
            context: RunnableConfig = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Union[dict, Command, Send, OutputT]:
        """"""
        logger.info(self.opening_symbols)
        logger.info(f"Number of messages: {len(state['messages'])}")

        # -------------------------------------------------------------------
        # This block is always executed only one time
        # store state from the official call (either to 'improve' or to 'generate')
        if not state['is_sub_call']:
            logger.info(f"Copy state call from '{state['caller']}'")
            logger.info(f'Number of queries: {len(state["queries"])}')
            self.copy_state = deepcopy(state)
            self.copy_state.pop('is_sub_call', None)
            self.copy_state.pop('has_docs', None)
            self.copy_state['num_queries'] = len(state['queries'])
            self.copy_state['query_offset'] = 0
            self.copy_state['previous_scripts'] = []
            self.get_retrieved_docs = False
        else:
            # 'fix' error task only can be called as inner call from 'improve' or 'generate' tasks
            pass

        if not state['has_docs']:
            logger.info("Call Retriever to get relevant documents")
            return DirectionRouter.goto(
                state={'coding_task': state['coding_task'],
                       'queries': state['queries']},
                node='retriever', method='send'
            )

        # store retrieved docs of first queries (official call)
        if not self.get_retrieved_docs:
            logger.info('Store retrieved docs')
            self.copy_state['retrieved_docs'] = state['retrieved_docs']
            self.get_retrieved_docs = True
        # inner call this agent must pass above blocks
        # -------------------------------------------------------------------
        # operate on each query
        try:
            # while generating and executing a script, the error message could be raised
            if state['coding_task'] == 'generate':
                formatted_prompt = self._prepare_generate_prompt(state)
            elif state['coding_task'] == "improve":
                assert 'current_script' in state
                formatted_prompt = self._prepare_improve_prompt(state)
            else:
                assert 'current_script' in state
                formatted_prompt = self._prepare_fix_prompt(state)

            script, messages = self._generate(formatted_prompt)
            # ------------error-free--------------------
            # the generated script is error-free,
            # it is also an ending point for recursive calls
            self.copy_state['previous_scripts'].append(script)
            self.copy_state['current_script'] = script
            self.copy_state['query_offset'] += 1
            self.copy_state['messages'] = messages

        except ScriptWithError as e:
            logger.info('‼️ ‼️ ‼️ ‼️ ‼️ ‼️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️️ Catch error. Call Retriever ⚠️ ⚠️ ⚠️ ⚠️ ⚠️️ ‼️‼️‼️‼️‼️‼️')
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
            return e.command

        # reset fix error tries after each query
        self.fix_error_tries = 0

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
            if self.save_scripts:
                self._save_all_scripts()

            # identify the next node based on the caller (i.e. previous node), only base on original call.
            if self.copy_state['caller'] == 'planner':
                next_node = 'critic'
            elif self.copy_state['caller'] == 'critic':
                next_node = 'verification'
            elif self.copy_state['caller'] == 'verification':
                next_node = 'verification'
            elif self.copy_state['caller'] == 'user':
                next_node = 'verification'
            else:
                next_node = END

            logger.info("✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ Finish a call, move to next node ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅")

        logger.info(self._used_token_prep())
        logger.info(f'coding -> {next_node}')
        logger.info(self.ending_symbols)

        # return stored original state ('copy_state' instead of 'state')
        # as there may be some sub calls from `retriever` that may change state.
        return DirectionRouter.goto(state=self.copy_state, node=next_node, method='command')

    def _prepare_prompt(self, state):
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

    @override
    def _prepare_chat_template(self, human_template, *args, **kwargs):
        return ChatPromptTemplate([self.system_template, human_template])

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

    def _prepare_generate_prompt(self, state):
        chat_template = self._prepare_chat_template(self.human_generate_template)

        # that's called only when coding_task is 'generate
        # when queries, from both of 'state' and 'copy_state', are subtasks
        query = state['queries'][self.copy_state['query_offset']]
        docs = state['retrieved_docs'][self.copy_state['query_offset']]

        logger.info(
            f"{state['coding_task']}: query {1 + self.copy_state['query_offset']}/{self.copy_state['num_queries']}: {query}")
        logger.info(f"Number of previous scripts: {len(self.copy_state['previous_scripts'])}")
        # ---------------------------------------------------
        formatted_prompt = chat_template.invoke({
            "subtask": query,
            "previous_scripts": self._dump_scripts(self.copy_state['previous_scripts']),
            "summary": docs
        })
        # ---------------------------------------------------
        return formatted_prompt

    def _prepare_fix_prompt(self, state):
        chat_template = self._prepare_chat_template(self.human_fix_template)

        logger.info(f"{state['coding_task']}: {self.fix_error_tries}(tries)/{self.fix_error_attempts}(attempts)")
        logger.info(f"error: {state['queries'][0]}")
        # ---------------------------------------------------
        formatted_prompt = chat_template.invoke({
            'current_script': state['current_script'],
            'error': state['queries'],
            'summary': state['retrieved_docs'][0]
        })
        # ---------------------------------------------------
        return formatted_prompt

    def _prepare_improve_prompt(self, state):
        chat_template = self._prepare_chat_template(self.human_improve_template)

        query = state['queries'][self.copy_state['query_offset']]
        docs = state['retrieved_docs'][self.copy_state['query_offset']]

        logger.info(
            f"{state['coding_task']}: solution {1 + self.copy_state['query_offset']}/{self.copy_state['num_queries']}")
        logger.info(f"solution: {query}")
        # ---------------------------------------------------
        formatted_prompt = chat_template.invoke({
            'current_script': state['current_script'],
            'solution': query,
            'summary': docs
        })
        # ---------------------------------------------------
        return formatted_prompt

    def _generate(self, formatted_prompt):
        while True:
            # ---------------------------Actual generation------------------------------
            generated_script, messages = self.chat_model_call(formatted_prompt)
            # --------------------------------------------------------------------------

            # call tool to write script
            write_script.invoke({
                "script": generated_script,
                "file_path": self.check_error_file
            })

            # call tool to execute script
            error = execute_script.invoke({'script': self.check_error_file})
            tool_message = self.create_tool_message(content=error, _id='call_execute_script')
            messages.append(tool_message)

            """Log conversation"""
            self.log_conversation(logger, messages)

            # no error yielded
            if 'no error' in error.lower():
                return generated_script, messages
            else:
                # raise the call to 'retriever' agent to fix error
                raise ScriptWithError(command=DirectionRouter.goto(
                    state={
                        'current_script': generated_script,
                        'coding_task': 'fix',
                        'queries': [error, ],
                        'messages': messages
                    },
                    node='retriever', method='command'
                ))

    def _dump_scripts(self, scripts):
        if not scripts:
            return []
        script_string = '=' * 150
        for script in scripts:
            script_string += "\n```python\n"
            script_string += script
            script_string += "\n```\n"
            script_string += '=' * 150 + '\n'

        return script_string

    def _save_all_scripts(self):
        caller_folder = os.path.join(self.script_folder, self.copy_state["caller"])
        os.makedirs(caller_folder, exist_ok=True)
        n = len(os.listdir(caller_folder))
        save_dir = os.path.join(caller_folder, str(n))
        os.makedirs(save_dir, exist_ok=True)

        for i, script in enumerate(self.copy_state['previous_scripts']):
            file = os.path.join(save_dir, f"script_{i}.py")
            write_script.invoke({
                'script': script,
                'file_path': file,
            })
        logger.info(f'Write all generated scripts to folder "{save_dir}"')
