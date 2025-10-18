import bpy

# Delete all materials before creating backrest
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create the backrest using wood material
# Define the parameters for the backrest
backrest_height = 0.5  # Height of the backrest
backrest_width = 1.0  # Width of the backrest
backrest_thickness = 0.1  # Thickness of the backrest
backrest_location = (0, 0, backrest_height + 0.1)  # Center of the backrest position

# Create a new cube for the backrest
bpy.ops.mesh.primitive_cube_add(size=1, location=backrest_location)
backrest = bpy.context.object
backrest.scale = (backrest_width / 2, backrest_thickness / 2, backrest_height / 2)  # Scale to the desired size

# Set the material for the backrest
backrest_mat = bpy.data.materials.new(name='Wood')
backrest_mat.use_nodes = True
bsdf = backrest_mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (0.6, 0.3, 0.1, 1)  # Brown color for wood
backrest.data.materials.append(backrest_mat)
