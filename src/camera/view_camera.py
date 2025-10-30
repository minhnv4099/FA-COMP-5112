#
#

#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import json as js
from argparse import ArgumentParser

import bpy


def get_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--temp_file',
        required=False,
        default='templates/camera_templates/template.json',
    )

    return parser.parse_args()


def main(args):
    camera_template_file = args.temp_file

    with open(camera_template_file, 'r') as f:
        camera_data = js.load(f)

    # Scene
    scene = bpy.context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1024

    for data in camera_data:
        # Create camera data block
        cam_data = bpy.data.cameras.new(name=data["name"])

        # cam_data.type = 'ORTHO'
        # cam_data.ortho_scale = 8.0  # giá trị càng nhỏ → zoom càng gần

        # Create camera object
        cam_object = bpy.data.objects.new(data["name"], cam_data)

        # Set position and rotation
        cam_object.location = data["location"]
        cam_object.rotation_euler = data["rotation_euler"]

        # Link to Scene Collection
        bpy.context.collection.objects.link(cam_object)


if __name__ == '__main__':
    args = get_args()
    main(args)
