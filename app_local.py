#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import sys
from typing import Any

import gradio as gr
import hydra
from omegaconf import DictConfig

from src.utils import find_load_env

repo_dir = os.path.dirname(__file__)
sys.path.extend((repo_dir, os.getcwd()))

find_load_env()

SYSTEM: Any
JOB_CONFIG: DictConfig
CONFIG_PATH = 'configs'
CONFIG_NAME = 'job'

progress = gr.Progress(track_tqdm=True)


@hydra.main(config_path=CONFIG_PATH, config_name=CONFIG_NAME, version_base=None)
def get_cfg(cfg):
    global JOB_CONFIG
    JOB_CONFIG = cfg


def build_system(cfg):
    from src.base.coordinator import Coordinator

    planner_agent = Coordinator.build_agent(agent_config=cfg.agent.planner)
    retriever_agent = Coordinator.build_agent(agent_config=cfg.agent.retriever)
    coding_agent = Coordinator.build_agent(agent_config=cfg.agent.coding)
    critic_agent = Coordinator.build_agent(agent_config=cfg.agent.critic)
    verification_agent = Coordinator.build_agent(agent_config=cfg.agent.verification)
    user_proxy_agent = Coordinator.build_agent(agent_config=cfg.agent.user)

    graph = Coordinator.build_graph(
        nodes=(
            planner_agent, retriever_agent, coding_agent,
            critic_agent, verification_agent, user_proxy_agent,),
        **cfg.graph
    )
    graph.init_graph()

    return graph


def create_image_area(_id):
    return gr.Image(
        label=f"Rendered image angele {_id}",
        interactive=False,
        width=300, height=300,
        visible=True
    )


def disable_interactive_comp(*compts):
    return [gr.update(interactive=False)] * len(compts)


def enable_interactive_comp(*compts):
    return [gr.update(interactive=True)] * len(compts)


def change_model(model_name):
    return model_name


def terminate():
    return execute(input_text, "quit")


def restart():
    global SYSTEM, JOB_CONFIG
    old_config = JOB_CONFIG
    get_cfg()
    if old_config != JOB_CONFIG:
        message = f"Restart system with new config"
        SYSTEM = build_system(JOB_CONFIG)
    else:
        message = f"It seems not to change anything"

    return message


if __name__ == '__main__':
    get_cfg()
    SYSTEM = build_system(JOB_CONFIG)
    n_images = JOB_CONFIG.agent.critic.n_rendered_images
    image_areas = []


    def execute(task, prompt):
        if not (task or prompt):
            return "Must provide task or prompt", '', '', *[None] * n_images
        results = SYSTEM(task, prompt)

        return results


    with (gr.Blocks() as demo):
        gr.Markdown("# Demo COMP-5112: Blender Code 3D Generation")

        input_text = gr.Textbox(
            label="Task (e.g. create a 3D chair). The program will prioritize using prompt,"
                  "make sure prompt area empty, if want to operate a new task. ",
            placeholder='Enter task...', lines=1)
        additional_prompt = gr.Textbox(
            label='Type additional prompt, "q" or "quit" to terminate',
            placeholder='Enter prompt...', lines=1)

        status_text = gr.Textbox(label='Status', lines=1)
        with gr.Row():
            script_output = gr.Textbox(label="The latest generated script", lines=15, show_copy_button=True)
            conversation_area = gr.Textbox(label="Conversation between agents", lines=15)

        with gr.Row(visible=True):
            # with gr.Column():
            image_areas.append(create_image_area(1))
            image_areas[-1]
            image_areas.append(create_image_area(2))
            image_areas[-1]
            # with gr.Column():
            image_areas.append(create_image_area(3))
            image_areas[-1]
            image_areas.append(create_image_area(4))
            image_areas[-1]

        with gr.Row():
            submit_button = gr.Button(value='Generate', interactive=True, min_width=20, scale=1)
            terminate_button = gr.Button(value='Terminate', interactive=True, visible=False, min_width=20, scale=1)
            restart_button = gr.Button(value='Restart with new config', interactive=True, min_width=20, scale=1)

        # This block modifies system configs
        with gr.Blocks() as config_modifier:
            coding_model_selector = gr.Dropdown(
                choices=[
                    "qwen/qwen3-coder:free",
                ],
                value="qwen/qwen3-coder:free",
                label="Model for Coding Agent",
                show_label=True,
                interactive=True,
                visible=False
            )

            coding_model_selector.change(change_model, inputs=coding_model_selector, outputs=coding_model_selector)

        interactive_compts = [input_text, additional_prompt, submit_button, terminate_button, restart_button,
                              coding_model_selector]

        submit_button.click(
            fn=disable_interactive_comp,
            inputs=interactive_compts,
            outputs=interactive_compts
        ).then(
            fn=execute,
            inputs=[input_text, additional_prompt],
            outputs=[status_text, script_output, conversation_area, *image_areas[:n_images]]
        ).then(
            fn=enable_interactive_comp,
            inputs=interactive_compts,
            outputs=interactive_compts
        )

        terminate_button.click(fn=terminate, inputs=[],
                               outputs=[input_text, additional_prompt])

        restart_button.click(fn=restart, inputs=[],
                             outputs=[status_text])

    demo.queue(max_size=100).launch(share=True, show_api=True)
