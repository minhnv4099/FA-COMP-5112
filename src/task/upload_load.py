#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os.path

from huggingface_hub import HfApi

hf = HfApi()


def hf_upload_file(
        file: str,
        repo_id: str,
        remote_path: str = None,
        revision: str = None,
        repo_type: str = None,
):
    assert os.path.isfile(file), f"'{file}' is not a file."
    if remote_path is None:
        remote_path = file
    if repo_type is None:
        repo_type = 'space'
    if revision is None:
        revision = 'main'

    hf.upload_file(
        repo_id=repo_id,
        path_in_repo=remote_path,
        path_or_fileobj=remote_path,
        revision=revision,
        repo_type=repo_type,
    )


def hf_upload_folder(
        folder: str,
        repo_id: str,
        repo_type: str = None,
        remote_path: str = None,
        revision: str = None
):
    assert os.path.isdir(folder), f"'{folder}' is not a folder."
    if remote_path is None:
        remote_path = folder
    if repo_type is None:
        repo_type = 'space'
    if revision is None:
        revision = 'main'

    hf.upload_large_folder(
        repo_id=repo_id,
        repo_type=repo_type,
        folder_path=folder,
        # path_in_repo=remote_path,
        revision=revision,
        ignore_patterns=[
            'test_*.py', 'tmp.py', '.env',
            'main.py', 'tests/', 'outputs/', 'models/', 'data/', '.gradio/'
        ],
    )


hf_upload_folder(
    repo_id='nguyenminh4099/COMP-5112',
    repo_type='dataset',
    revision='main',
    folder='data/',
    remote_path='data/'
)
