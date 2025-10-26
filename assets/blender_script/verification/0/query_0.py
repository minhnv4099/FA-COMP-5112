import bmesh
import bpy


# Clear existing objects
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


# Create a modeled character with basic features and cartoonish shape
def create_character():
    # Add a basic body structure
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
    character_body = bpy.context.object
    character_body.name = "CharacterBody"

    # Add head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 1.5))
    character_head = bpy.context.object
    character_head.name = "CharacterHead"

    # Add eyes
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(-0.2, 0.2, 1.8))
    left_eye = bpy.context.object
    left_eye.name = "LeftEye"

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0.2, 0.2, 1.8))
    right_eye = bpy.context.object
    right_eye.name = "RightEye"

    # Add mouth
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.05, location=(0, -0.1, 1.5))
    mouth = bpy.context.object
    mouth.name = "Mouth"

    # Add nose
    bpy.ops.mesh.primitive_cone_add(radius1=0.1, depth=0.3, location=(0, 0.05, 1.7))
    nose = bpy.context.object
    nose.name = "Nose"

    # Add limbs (basic cylindrical shapes for arms and legs)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1, location=(-0.5, 0, 0))
    left_arm = bpy.context.object
    left_arm.name = "LeftArm"

    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1, location=(0.5, 0, 0))
    right_arm = bpy.context.object
    right_arm.name = "RightArm"

    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1, location=(-0.2, 0, -0.75))
    left_leg = bpy.context.object
    left_leg.name = "LeftLeg"

    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1, location=(0.2, 0, -0.75))
    right_leg = bpy.context.object
    right_leg.name = "RightLeg"

    # Using Remesh Modifier to ensure smooth cartoonish shape
    for obj in [left_eye, right_eye, mouth, nose, left_arm, right_arm, left_leg, right_leg]:
        bpy.context.view_layer.objects.active = obj
        remesh_modifier = obj.modifiers.new(name='Remesh', type='REMESH')
        remesh_modifier.mode = 'SMOOTH'
        remesh_modifier.octree_depth = 4
        remesh_modifier.use_remove_disconnected = True  # Remove disconnected elements for cleaner topology
        remesh_modifier.use_smooth_shade = True

    # Group components into a collection
    character_collection = bpy.data.collections.new("CharacterCollection")
    bpy.context.scene.collection.children.link(character_collection)

    # Link all parts to the collection
    for part in [character_body, character_head, left_eye, right_eye, mouth, nose, left_arm, right_arm, left_leg,
                 right_leg]:
        character_collection.objects.link(part)

    print("Character with enhanced features and unique silhouette created.")


# Function to paint features on character
def paint_character_features():
    # Ensure we're in texture paint mode
    bpy.ops.object.mode_set(mode='TEXTURE_PAINT')

    # Select the appropriate brush
    bpy.ops.paint.brush_select()
    # Set brush and falloff settings for detail painting
    brush = bpy.data.brushes.get('TexDraw')
    if brush:
        brush.use_paint_sculpt = True
        brush.falloff_shape = 'SPHERE'  # Using spherical falloff for smooth transitions
        brush.strength = 0.5

    # Make sure an image is active in the UV/Image Editor before painting
    # To fix the context issue, confirm the current object has a texture
    current_object = bpy.context.active_object
    if current_object and current_object.data.materials:
        material = current_object.data.materials[0]
        if material and material.use_nodes:
            nodes = material.node_tree.nodes
            image_texture_node = nodes.get('Image Texture')
            if image_texture_node and image_texture_node.image:
                # Set the context to image paint for the current object
                bpy.ops.paint.image_paint()
            else:
                print("No image found for painting.")
        else:
            print("Material nodes not set up properly.")
    else:
        print("No material or texture available for current object.")

    print("Character features painted with cartoonish details.")


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
    armature = bpy.data.objects.get('CharacterArmature')
    if armature:
        armature_modifier.object = armature

    print("Character clothing with cloth simulation and armature integration created.")


# Function to enhance clothing design with remesh for cartoonish shape
def remesh_character_clothing(clothing):
    remesh_modifier = clothing.modifiers.new(name='Remesh', type='REMESH')
    remesh_modifier.mode = 'SMOOTH'
    remesh_modifier.octree_depth = 4
    remesh_modifier.use_remove_disconnected = False
    remesh_modifier.use_smooth_shade = True

    print("Character clothing remeshed for a cartoonish shape.")


# Function to enhance scene with multiple dynamic lights
def enhance_scene_with_dynamic_lighting():
    # Key Light
    bpy.ops.object.light_add(type='SUN', radius=1, location=(5, -5, 5))
    key_light = bpy.context.object
    key_light.name = "KeyLight"
    key_light.data.energy = 10

    # Fill Light
    bpy.ops.object.light_add(type='AREA', radius=3, location=(-4, 4, 2))
    fill_light = bpy.context.object
    fill_light.name = "FillLight"
    fill_light.data.energy = 4

    # Back Light
    bpy.ops.object.light_add(type='SPOT', radius=1, location=(0, 0, 5))
    back_light = bpy.context.object
    back_light.name = "BackLight"
    back_light.data.energy = 7

    # Additional Light for Dynamics
    bpy.ops.object.light_add(type='POINT', radius=1, location=(3, -3, 1))
    additional_light = bpy.context.object
    additional_light.name = "DynamicLight"
    additional_light.data.energy = 6

    print("Multiple dynamic lighting setup added to the scene.")


# Main execution
def main():
    clear_scene()
    create_character()
    paint_character_features()
    design_character_clothing()
    clothing = bpy.data.objects.get("CharacterClothing")
    if clothing:
        remesh_character_clothing(clothing)
    enhance_scene_with_dynamic_lighting()


# Execute the main function
if __name__ == "__main__":
    main()
