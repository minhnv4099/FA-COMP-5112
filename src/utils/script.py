#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import subprocess


# def combine_and_write(script_path: str, additional_path: str = None):
#     with open(script_path, mode='r') as f:
#         creation_script = f.read()
#
#     if additional_path is None:
#         additional_path = DEFAULT_CAMERA_SETTING_FILE
#
#     with open(additional_path, mode='r') as f:
#         camera_script = f.read()
#
#     script = f"""{creation_script}
#
# {camera_script}
# """
#
#     with open(ANCHOR_FILE, 'w') as f:
#         f.write(script)
#
#     return ANCHOR_FILE


def execute(script_path: str):
    python_option = '--python'

    process = subprocess.Popen(
        args=['blender', '--background', python_option, script_path],
        shell=False,
        restore_signals=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    result = {"error": stderr, 'stdout': stdout, 'returncode': process.returncode}

    process.terminate()
    process.kill()
    process.wait()

    return result


def write_script(script: str, file_path: str) -> None:
    """Write a python script to a file with file path

    Args:
        script (str): Script need to write
        file_path (str|Path): Destination will contain the script

    Returns: None
    """
    with open(file_path, mode='w') as f:
        f.write(script)
