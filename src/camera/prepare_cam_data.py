import json as js

import bpy

camera_template_file = '{{camera_template_file}}'
save_dir = "{{save_dir}}"

with open(camera_template_file, 'r') as f:
    camera_data = js.load(f)

# Scene
scene = bpy.context.scene

scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1024

cameras = []
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

    # Save object and file path
    cameras.append({
        "object": cam_object,
        "filepath": data["filepath"].format(save_dir=save_dir)
    })
