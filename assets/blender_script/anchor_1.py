import bpy

# Delete all objects before creating the seat base
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create the seat base using wood material
# Define the parameters for the seat
seat_height = 0.1  # Height of the seat
seat_width = 1.0  # Width of the seat
seat_length = 1.0  # Length of the seat
seat_location = (0, 0, seat_height)  # Center of the seat base

# Create a new cube for the seat base
bpy.ops.mesh.primitive_cube_add(size=1, location=seat_location)
seat_base = bpy.context.object
seat_base.scale = (seat_width / 2, seat_length / 2, seat_height / 2)  # Scale to the desired size

# Set the material for the seat base
seat_mat = bpy.data.materials.new(name='Wood')
seat_mat.use_nodes = True
bsdf = seat_mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (0.6, 0.3, 0.1, 1)  # Brown color for wood
seat_base.data.materials.append(seat_mat)
