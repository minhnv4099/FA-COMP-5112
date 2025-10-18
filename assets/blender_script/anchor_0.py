import bpy

# Delete all materials before creating chair legs
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
