import bmesh
import bpy

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


# Function to design character clothing with collision and armature integration
def design_character_clothing():
    # Add a new mesh for the clothing
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 1))
    clothing = bpy.context.object
    clothing.name = "CharacterClothing"

    # Add Cloth Physics
    cloth_modifier = clothing.modifiers.new(name='Cloth', type='CLOTH')
    clothing_mod_settings = cloth_modifier.settings
    clothing_collision_settings = cloth_modifier.collision_settings

    # Configure cloth settings
    clothing_mod_settings.quality = 5
    clothing_mod_settings.mass = 0.3

    # Configure collision settings
    clothing_collision_settings.use_collision = True
    clothing_collision_settings.self_friction = 5.0

    # Add armature modifier to clothing to bind it with character's skeleton
    armature_modifier = clothing.modifiers.new(name='Armature', type='ARMATURE')
    armature_modifier.object = bpy.data.objects.get('CharacterArmature')

    print("Character clothing with cloth simulation and armature integration created.")


# Execute the function to design the character's clothing
design_character_clothing()

# Scene
scene = bpy.context.scene

# Cài đặt output render
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1024

x_axis = 7
y_axis = 7
z_axis = 2.5

x_angle = 75
y_angle = 0
z_angle = 90

save_dir = "assets/rendered_images/critic//0"

import math
from mathutils import Vector

camera_data = [
    {
        "name": "Camera_A",
        "location": (6.9017, -6.3911, 3.3923),
        "rotation_euler": (math.radians(70.4027), math.radians(0), math.radians(46.201)),  # Nhìn vào (0,0,0) từ góc
        "filepath": f"{save_dir}/render_A_"
    },
    {
        "name": "Camera_B",
        "location": Vector((-7.15066, 5.72361, 2.81074)),
        # "location": (-x_axis, 0, z_axis),
        "rotation_euler": (math.radians(72.8002), math.radians(0), math.radians(231.401)),
        # Nhìn vào (0,0,0) từ góc khác
        "filepath": f"{save_dir}/render_B_"
    },
    {
        "name": "Camera_C",
        "location": (7.18658, 5.90272, 2.99018),
        "rotation_euler": (math.radians(72.4005), math.radians(0), math.radians(-229.801)),  # Nhìn vào (0,0,0) từ góc
        "filepath": f"{save_dir}/render_C_"
    },
    {
        "name": "Camera_D",
        "location": (-6.93296, -7.38291, 3.89864),
        "rotation_euler": (math.radians(68.4036), math.radians(0), math.radians(-44.2024)),  # Nhìn vào (0,0,0) từ góc
        "filepath": f"{save_dir}/render_D_"
    },
    # {
    #     "name": "Camera_E",
    #     "location": (-5.70548, 4.69015, 1.94329),
    #     "rotation_euler": (math.radians(76.8001), math.radians(0), math.radians(228.601)),  # Nhìn vào (0,0,0) từ góc
    #     "filepath": f"{save_dir}/render_E_"
    # },
    # {
    #     "name": "Camera_F",
    #     "location": (5.24471, 3.51796, 1.29235),
    #     "rotation_euler": (math.radians(78.8004), math.radians(0), math.radians(-235.001)),  # Nhìn vào (0,0,0) từ góc
    #     "filepath": f"{save_dir}/render_F_"
    # },
    # {
    #     "name": "Camera_G",
    #     "location": (5.17812, -4.54725, 2.1893),
    #     "rotation_euler": (math.radians(72.8017), math.radians(0), math.radians(47.4005)),  # Nhìn vào (0,0,0) từ góc
    #     "filepath": f"{save_dir}/render_G_"
    # },
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

# ----------------------------------------
# Render and Save images from each Camera angle
# ----------------------------------------

for cam in cameras:
    # 1. Set up a working Camera for the Scene
    scene.camera = cam["object"]

    # 2. Set a specific output path for this render
    scene.render.filepath = cam["filepath"]

    # 3. Execute the render command and save the still image (write_still=True)
    bpy.ops.render.render(write_still=True)

print("Render images successfully")
