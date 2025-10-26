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

    # Group components into a collection
    character_collection = bpy.data.collections.new("CharacterCollection")
    bpy.context.scene.collection.children.link(character_collection)

    # Link all parts to the collection
    for part in [character_body, character_head, left_eye, right_eye, mouth]:
        character_collection.objects.link(part)

    print("Character with basic features created.")


# Function to paint features on character
def paint_character_features():
    # Ensure we're in texture paint mode
    bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
    # Select the appropriate brush
    bpy.ops.paint.brush_select()
    # Set brush and falloff settings for detail painting
    brush = bpy.data.brushes['TexDraw']
    brush.use_paint_sculpt = True
    brush.falloff_shape = 'SPHERE'
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
    armature_modifier.object = bpy.data.objects.get('CharacterArmature')

    print("Character clothing with cloth simulation and armature integration created.")


# Function to enhance clothing design with remesh for cartoonish shape
def remesh_character_clothing(clothing):
    remesh_modifier = clothing.modifiers.new(name='Remesh', type='REMESH')
    remesh_modifier.mode = 'SMOOTH'
    remesh_modifier.octree_depth = 4
    remesh_modifier.use_remove_disconnected = False
    remesh_modifier.use_smooth_shade = True

    print("Character clothing remeshed for a cartoonish shape.")


# Enhance scene with lighting and shadow settings
def enhance_scene_with_shadows():
    # Enable shadows and set shadow settings using available attributes
    for light in bpy.data.lights:
        if light.type == 'POINT':
            light.shadow_soft_size = 0.1  # Set soft shadow size
            light.use_shadow = True

    # Enable ambient occlusion
    bpy.context.scene.eevee.use_gtao = True

    # Enable Screen Space Reflections (approximate ray tracing)
    bpy.context.scene.eevee.use_ssr = True

    # Adjust Color Management Settings for better contrast
    scene = bpy.context.scene
    # Remove use of the deprecated or non-existing 'use_hdr_view'
    scene.view_settings.view_transform = 'Filmic'  # Use Filmic to enhance dynamic range

    print("Scene enhanced with lighting, shadow settings, and improved contrast.")


# Main execution
def main():
    clear_scene()
    create_character()
    paint_character_features()
    design_character_clothing()
    clothing = bpy.data.objects.get("CharacterClothing")
    if clothing:
        remesh_character_clothing(clothing)
    enhance_scene_with_shadows()


# Execute the main function
main()
