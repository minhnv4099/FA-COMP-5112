import os
import sys
import gradio as gr
import hydra
from hydra import initialize, compose
from hydra.core.hydra_config import HydraConfig
from hydra.core.utils import configure_log
from omegaconf import DictConfig

repo_dir = os.path.dirname(__file__)
sys.path.extend((repo_dir, os.getcwd()))

try:
    from dotenv import load_dotenv

    load_dotenv()
except FileNotFoundError as e:
    pass

JOB_CONFIG: DictConfig
CONFIG_PATH = 'configs'
CONFIG_NAME = 'job'


@hydra.main(config_path="configs", config_name="job", version_base=None)
def get_cfg(cfg):
    global JOB_CONFIG
    JOB_CONFIG = cfg


def build_graph(cfg):
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


def disable_interactive_comp():
    return [
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
    ]


def enable_interactive_comp():
    return [
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
    ]


can_type_new_task = True

# def main(cfg):
#     def change_model(a):
#         cfg.agent.coding.model_name = a
#
#     graph = build_graph(cfg)
#
#     def execute(task, prompt):
#         global can_type_new_task
#         assert task, 'Must provide task'
#         response = graph(task, prompt)
#         # if can_type_new_task is False:
#         #     assert prompt
#         #     response = graph(prompt)
#         # else:
#         #     response = graph(task)
#
#         can_type_new_task = False
#
#         return response
#
#     def start_app():
#         try:
#             global can_type_new_task
#             demo.queue(max_size=100).launch(share=True, show_api=True)
#             can_type_new_task = True
#         except AttributeError as e:
#             pass
#         return [
#             gr.update(interactive=False),
#             gr.update(interactive=False),
#             gr.update(interactive=False),
#             gr.update(interactive=False),
#         ]
#
#     with (gr.Blocks() as demo):
#         input_text = gr.Textbox(label="Task (e.g. create a 3D chair)", placeholder='Enter task...', lines=1)
#         additional_prompt = gr.Textbox(label='Type additional prompt', placeholder='Enter prompt...', lines=1)
#
#         status_text = gr.Textbox(label='Status', lines=1)
#         script_output = gr.Textbox(label="The final generated script", lines=10)
#         conversation_area = gr.Textbox(label="Conversation between agents", lines=10)
#
#         image_areas = [
#             gr.Image(
#                 label=f"Rendered image angele {i}",
#                 interactive=True,
#                 width=500, height=500
#             )
#             for i in range(4)
#         ]
#
#         submit_button = gr.Button(value='Generate', interactive=True)
#         terminate_button = gr.Button(value='Terminate', interactive=True)
#         restart_button = gr.Button(value='Stop and restart', interactive=True)
#
#         submit_button.click(
#             fn=disable_interactive_comp,
#             inputs=[],
#             outputs=[input_text, additional_prompt, submit_button, terminate_button],
#         ).then(
#             fn=execute,
#             inputs=[input_text, additional_prompt],
#             outputs=[status_text, script_output, conversation_area, image_areas[0]],
#         ).then(
#             fn=enable_interactive_comp,
#             inputs=[],
#             outputs=[input_text, additional_prompt, submit_button, terminate_button],
#         )
#
#         restart_button.click(fn=start_app, inputs=[], outputs=[input_text, additional_prompt, submit_button, terminate_button])
#         terminate_button.click(fn=start_app, inputs=[], outputs=[input_text, additional_prompt, submit_button, terminate_button])
#
#         with gr.Blocks() as model_selector:
#             coding_model_selector = gr.Dropdown(
#                 choices=["gpt-4o", "gpt-4o-mini"],
#                 value="gpt-4o-mini",
#                 label="Model for Coding Agent",
#                 show_label=True,
#                 interactive=True,
#             )
#             coding_model_selector.change(change_model, inputs=coding_model_selector)
#
#     start_app()


if __name__ == '__main__':
    get_cfg()
    graph = build_graph(JOB_CONFIG)


    def change_model(a):
        JOB_CONFIG.agent.coding.model_name = a


    def execute(task, prompt):
        global can_type_new_task
        assert task, 'Must provide task'
        response = graph(task, prompt)
        # if can_type_new_task is False:
        #     assert prompt
        #     response = graph(prompt)
        # else:
        #     response = graph(task)

        can_type_new_task = False

        return response


    def start_app():
        try:
            global can_type_new_task
            demo.queue(max_size=100).launch(share=True, show_api=True)
            can_type_new_task = True
        except AttributeError as e:
            pass
        return [
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
        ]


    with (gr.Blocks() as demo):
        input_text = gr.Textbox(label="Task (e.g. create a 3D chair)", placeholder='Enter task...', lines=1)
        additional_prompt = gr.Textbox(label='Type additional prompt', placeholder='Enter prompt...', lines=1)

        status_text = gr.Textbox(label='Status', lines=1)
        script_output = gr.Textbox(label="The final generated script", lines=10)
        conversation_area = gr.Textbox(label="Conversation between agents", lines=10)

        image_areas = [
            gr.Image(
                label=f"Rendered image angele {i}",
                interactive=True,
                width=500, height=500
            )
            for i in range(4)
        ]

        submit_button = gr.Button(value='Generate', interactive=True)
        terminate_button = gr.Button(value='Terminate', interactive=True)
        restart_button = gr.Button(value='Stop and restart', interactive=True)

        submit_button.click(
            fn=disable_interactive_comp,
            inputs=[],
            outputs=[input_text, additional_prompt, submit_button, terminate_button],
        ).then(
            fn=execute,
            inputs=[input_text, additional_prompt],
            outputs=[status_text, script_output, conversation_area, image_areas[0]],
        ).then(
            fn=enable_interactive_comp,
            inputs=[],
            outputs=[input_text, additional_prompt, submit_button, terminate_button],
        )

        restart_button.click(fn=start_app, inputs=[],
                             outputs=[input_text, additional_prompt, submit_button, terminate_button])
        terminate_button.click(fn=start_app, inputs=[],
                               outputs=[input_text, additional_prompt, submit_button, terminate_button])

        with gr.Blocks() as model_selector:
            coding_model_selector = gr.Dropdown(
                choices=["gpt-4o", "gpt-4o-mini"],
                value="gpt-4o-mini",
                label="Model for Coding Agent",
                show_label=True,
                interactive=True,
            )
            coding_model_selector.change(change_model, inputs=coding_model_selector)

    start_app()
