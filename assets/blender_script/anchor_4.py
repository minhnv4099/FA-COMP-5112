import bpy

# Delete all objects and materials before creating the chair
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create chair legs using wood material
# Define the parameters for the legs
height = 1.0  # Height of the legs
radius = 0.05  # Radius of the legs
legs_positions = [(-0.5, -0.5, 0), (0.5, -0.5, 0), (-0.5, 0.5, 0), (0.5, 0.5, 0)]  # Positions of the legs

for pos in legs_positions:
    # Create a new cylinder for each leg
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height, location=pos)
    leg = bpy.context.object
    # Set the material for the leg
    mat = bpy.data.materials.new(name='Wood')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (0.6, 0.3, 0.1, 1)  # Brown color for wood
    leg.data.materials.append(mat)

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
