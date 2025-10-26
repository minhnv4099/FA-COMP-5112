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


# Function to create a more complex character with layers for depth
def create_complex_character_with_layers():
    # Add a simplified basic character
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
    character_body = bpy.context.object
    character_body.name = "CharacterBody"

    # Use the original function for clothing
    design_character_clothing()

    # Add additional feature: a sphere as a head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 1.5))
    character_head = bpy.context.object
    character_head.name = "CharacterHead"

    # Create a new collection and link objects to the collection
    complex_character_collection = bpy.data.collections.new("ComplexCharacterCollection")
    bpy.context.scene.collection.children.link(complex_character_collection)

    # Link objects to the collection
    complex_character_collection.objects.link(character_body)
    complex_character_collection.objects.link(character_head)
    complex_character_collection.objects.link(bpy.data.objects['CharacterClothing'])

    print("Complex character with collections created.")


# Execute the function to create a complex character
create_complex_character_with_layers()
