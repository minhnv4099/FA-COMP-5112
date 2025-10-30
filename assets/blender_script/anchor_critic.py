import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


# Function to create a table using mesh primitives

def create_table():
    # Create the tabletop
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))  # Top part of the table
    tabletop = bpy.context.active_object
    tabletop.name = 'Tabletop'
    bpy.ops.transform.resize(value=(1.5, 0.8, 0.1))  # Resize to appropriate dimensions

    # Create the legs
    leg_positions = [(1.3, 0.8, 0.5), (-1.3, 0.8, 0.5), (1.3, -0.8, 0.5), (-1.3, -0.8, 0.5)]
    for pos in leg_positions:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1, location=pos)  # Create a leg
        leg = bpy.context.active_object
        leg.name = 'TableLeg'


# Call the function to create the table
create_table()


class MyTableLayout(bpy.types.Panel):
    bl_label = "Table Layout"
    bl_idname = "PT_TableLayout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout

        # Example of using row() for table layout
        row = layout.row()
        row.prop(context.scene, 'some_property')  # Replace with actual property

        # Example of using column() for vertical alignment
        col = layout.column()
        col.label(text="Table Header")
        col.prop(context.scene, 'another_property')  # Replace with actual property

        # Example of using grid_flow() for grid layout
        grid = layout.grid_flow(columns=2, even_columns=True)
        grid.operator('object.select_all')
        grid.operator('object.delete')

        # Select and list materials for the table
        materials = bpy.data.materials
        for material in materials:
            layout.prop(material, 'name', text=material.name)  # List materials


def register():
    bpy.utils.register_class(MyTableLayout)


def unregister():
    bpy.utils.unregister_class(MyTableLayout)


if __name__ == "__main__":
    register()

import bpy
import json as js

camera_template_file = 'templates/camera_templates/template.json'
save_dir = "assets/rendered_images/critic/3"

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

for cam in cameras:
    scene.camera = cam["object"]
    scene.render.filepath = cam["filepath"]
    bpy.ops.render.render(write_still=True)
