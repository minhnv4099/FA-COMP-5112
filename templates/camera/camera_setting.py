import math
from mathutils import Vector
import bpy

# Scene
scene = bpy.context.scene

scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1024

save_dir = "{{save_dir}}"

camera_data = [
    {
        "name": "Camera_A",
        "location": (9.55091, -11.0553, 3.26154),
        "rotation_euler": (math.radians(80.0037), math.radians(0), math.radians(40.2015)),
        "filepath": f"{save_dir}/render_A_"
    },
    {
        "name": "Camera_B",
        "location": Vector((-9.51629, 10.6913, 5.08474)),
        "rotation_euler": (math.radians(73.2004), math.radians(0), math.radians(221)),  # Nhìn vào (0,0,0) từ góc khác
        "filepath": f"{save_dir}/render_B_"
    },
    {
        "name": "Camera_C",
        "location": (9.72838, 10.8774, 4.44635),
        "rotation_euler": (math.radians(75.6007), math.radians(0), math.radians(-223.001)),  # Nhìn vào (0,0,0) từ góc
        "filepath": f"{save_dir}/render_C_"
    },
    {
        "name": "Camera_D",
        "location": (-9.78594, -10.9808, 3.79748),
        "rotation_euler": (math.radians(77.6037), math.radians(0), math.radians(-41.8024)),  # Nhìn vào (0,0,0) từ góc
        "filepath": f"{save_dir}/render_D_"
    },
]

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
    cameras.append({"object": cam_object, "filepath": data["filepath"]})
