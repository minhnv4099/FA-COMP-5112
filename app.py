import gradio as gr
import hydra

from src.base.coordinator import Coordinator

try:
    from dotenv import load_dotenv

    load_dotenv('.env')
except FileNotFoundError as e:
    pass


def build_graph(cfg):
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


@hydra.main(config_path="configs", config_name="job", version_base=None)
def main(cfg):
    def change_model(a):
        cfg.agent.coding.model_name = a

    def execute(task):
        assert task, 'Must provide task'
        submit_button.interactive = False
        input_text.interactive = False

        graph = build_graph(cfg)
        response = graph(task)

        submit_button.interactive = True
        input_text.interactive = True

        return response

    def disable_button():
        return gr.update(interactive=False)

    def enable_button():
        return gr.update(interactive=True)

    with (gr.Blocks() as demo):
        input_text = gr.Textbox(label="Task (e.g. create a 3D chair)", placeholder='Enter task...', lines=1)
        script_output = gr.Textbox(label="The final generated script", lines=20)
        conversation_area = gr.Textbox(label="Conversation between agents", lines=30)
        status_text = gr.Textbox(label='Status', lines=1)

        submit_button = gr.Button(value='Generate', interactive=True)

        submit_button.click(
            fn=disable_button,
            inputs=[],
            outputs=submit_button,
        ).then(
            fn=execute,
            inputs=[input_text],
            outputs=[status_text, script_output, conversation_area],
        ).then(
            fn=enable_button,
            inputs=[],
            outputs=submit_button,
        )

        with gr.Blocks() as model_selector:
            coding_model_selector = gr.Dropdown(
                choices=["gpt-4o", "gpt-4o-mini"],
                value="gpt-4o-mini",
                label="Model for Coding Agent",
                show_label=True,
                interactive=True,
            )
            coding_model_selector.change(change_model, inputs=coding_model_selector)

    demo.queue(max_size=100).launch(share=True, show_api=True)


if __name__ == '__main__':
    main()
