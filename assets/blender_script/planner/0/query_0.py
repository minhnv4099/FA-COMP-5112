import bpy

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


# Function to define the character's body shape
def design_character_body():
    # Create an armature object for the character's bones
    bpy.ops.object.armature_add()
    armature = bpy.context.object
    armature.name = "CharacterArmature"

    # Enter edit mode to modify the armature
    bpy.ops.object.mode_set(mode='EDIT')

    # Adjust bones using PoseBones
    for bone in armature.data.edit_bones:
        bone.head = (0, 0, 1)  # Set position
        bone.tail = (0, 1, 1)  # Set length and direction

    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Access pose bones to alter properties
    for bone in armature.pose.bones:
        bone.custom_shape_translation[1] = 0.1  # Position adjustment
        # bone.disable_bone_shape = True  # This line is removed because PoseBone does not have the attribute
        # bone.bone_shape_scale_factor = 1.0  # Commented out as there is no equivalent attribute in PoseBone

    print("Character armature designed with initial pose bones setup.")


# Execute the function to design the character body
design_character_body()
