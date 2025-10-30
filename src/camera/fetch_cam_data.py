#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
CAM_TEMPLATE_DIR = "templates/camera_templates/"


def fetch_camera_data():
    import os
    import bpy
    import json as js

    os.makedirs(CAM_TEMPLATE_DIR, exist_ok=True)
    cam_template_file = os.path.join(CAM_TEMPLATE_DIR, f"template_{len(os.listdir(CAM_TEMPLATE_DIR))}.json")

    cameras = []
    for obj in bpy.data.objects:
        camera = dict()
        if obj.type == 'CAMERA':
            camera['name'] = obj.name
            camera['location'] = tuple(obj.location)
            camera['rotation_euler'] = tuple(obj.rotation_euler)
            camera['filepath'] = "{save_dir}/" + obj.name

        if camera:
            cameras.append(camera)

    with open(cam_template_file, 'w') as f:
        js.dump(obj=cameras, fp=f, indent=4)


fetch_camera_data()
