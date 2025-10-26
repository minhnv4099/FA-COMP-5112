---
title: 5112_project
app_file: app.py
sdk: gradio
sdk_version: 5.49.1
---
# 3D Blender code generation

## Install requirements

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py --task=<create a 3d chair>
```

## Files structure

``` 
├── .gitignore
├── README.md
├── LISCENSE
├── main.py
├── configs
|   ├── job.yaml
|   ├── graph.yaml
|   ├── hydra.ymal
|   └── agents
|       ├── coding.yaml
|       ├── critic.yaml
|       ├── planner.yaml
|       ├── retriever.yaml
|       ├── user.yaml
|       └── verification.yaml
|
├── src
|   ├── base
|   |   ├── agent.py
|   |   ├── coordinator.py
|   |   ├── graph.py
|   |   ├── mapping.py
|   |   ├── state.py
|   |   ├── structured_output.py
|   |   ├── tool.py
|   |   └── utils.py
|   ├── agents  
|   |   ├── coding.py
|   |   ├── critic.py
|   |   ├── planner.py
|   |   ├── retriever.py
|   |   ├── user.py
|   |   └── verification.py
|   ├── task  
|   |   ├── convert_html_to_pdf.py
|   |   └── prepare_db.py
|   └── utils.py
|  
├── templates
|   ├── prompt
|   |   ├── coding.yaml
|   |   ├── critic.yaml
|   |   ├── planner.yaml
|   |   ├── retriever.yaml
|   |   └── verification.yaml
|   └── camera_setting
|
├── vectorstores
|   ├── camera_setting
|   └── faiss
|       ├── index.faiss
|       └── index.pkl
|
└── data
    ├── external
    |   └── blender_document_html
    |       ├── file_1.html
    |       ├── ...
    |       └──fiel_n.html
    └── interm
        └── blender_document_pdf
            ├── file_1.pdf
            ├── ...
            └── fiel_n.pdf
```

## Test Demo

[Demo here](https://huggingface.co/spaces/nguyenminh4099/5112_project/tree/main)

## References