import bpy

# Delete all materials before creating armrests
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create armrests using wood material
# Define the parameters for the armrests
armrest_height = 0.1  # Height of the armrests
armrest_width = 0.1  # Width of the armrests
armrest_length = 0.5  # Length of the armrests
armrest_offset = 0.4  # Offset from the backrest position

# Create armrests positions
left_armrest_location = (-armrest_offset, 0, armrest_height + 0.1)  # Left armrest position
right_armrest_location = (armrest_offset, 0, armrest_height + 0.1)  # Right armrest position

# Create a new cube for the left armrest
bpy.ops.mesh.primitive_cube_add(size=1, location=left_armrest_location)
left_armrest = bpy.context.object
left_armrest.scale = (armrest_length / 2, armrest_width / 2, armrest_height / 2)  # Scale to the desired size

# Set the material for the left armrest
armrest_mat = bpy.data.materials.new(name='Wood')
armrest_mat.use_nodes = True
bsdf = armrest_mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (0.6, 0.3, 0.1, 1)  # Brown color for wood
left_armrest.data.materials.append(armrest_mat)

# Create a new cube for the right armrest
bpy.ops.mesh.primitive_cube_add(size=1, location=right_armrest_location)
right_armrest = bpy.context.object
right_armrest.scale = (armrest_length / 2, armrest_width / 2, armrest_height / 2)  # Scale to the desired size

# Set the material for the right armrest
right_armrest.data.materials.append(armrest_mat)
