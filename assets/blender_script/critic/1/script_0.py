import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Ensure we are working with the armature
armature = bpy.data.objects.new('DogArmature', bpy.data.armatures.new('DogArmatureData'))
bpy.context.collection.objects.link(armature)
bpy.context.view_layer.objects.active = armature
armature.select_set(True)

# Switch to Edit Mode
bpy.ops.object.mode_set(mode='EDIT')

# Access edit bones
edit_bones = bpy.context.object.data.edit_bones

# Create the body bone
edit_bone = edit_bones.new('DogBodyBone')
edit_bone.head = (0, 0, 0)  # Start position of the bone
edit_bone.tail = (0, 0, 1)  # End position of the bone
edit_bone.roll = 0  # Adjust roll if necessary

# Create the head bone for the dog
head_bone = edit_bones.new('DogHeadBone')
head_bone.head = (0, 0, 1)  # Position adjusted for the head
head_bone.tail = (0, 0, 1.5)  # Length and position of the head bone
head_bone.parent = edit_bone  # Set the body bone as the parent

# Create legs for the dog
# Front left leg
front_left_leg = edit_bones.new('FrontLeftLegBone')
front_left_leg.head = (0, 0, 0)  # Position aligned with the body
front_left_leg.tail = (0.3, 0, 0)  # Position extending outward
front_left_leg.parent = edit_bone  # Parent to the body bone

# Front right leg
front_right_leg = edit_bones.new('FrontRightLegBone')
front_right_leg.head = (0, 0, 0)  # Position aligned with the body
front_right_leg.tail = (0.3, 0, 0)  # Position extending outward
front_right_leg.parent = edit_bone  # Parent to the body bone

# Back left leg
back_left_leg = edit_bones.new('BackLeftLegBone')
back_left_leg.head = (0, -0.5, 0)  # Position aligned with the body
back_left_leg.tail = (0.3, -0.5, 0)  # Position extending outward
back_left_leg.parent = edit_bone  # Parent to the body bone

# Back right leg
back_right_leg = edit_bones.new('BackRightLegBone')
back_right_leg.head = (0, -0.5, 0)  # Position aligned with the body
back_right_leg.tail = (0.3, -0.5, 0)  # Position extending outward
back_right_leg.parent = edit_bone  # Parent to the body bone

# Exit Edit Mode
bpy.ops.object.mode_set(mode='OBJECT')

# Create a new Mesh for the dog's head
head_mesh = bpy.data.meshes.new('DogHeadMesh')
head_object = bpy.data.objects.new('DogHead', head_mesh)
bpy.context.collection.objects.link(head_object)

# Adding a particle system for fur
bpy.context.view_layer.objects.active = head_object
head_object.select_set(True)

# Create particle system 
particle_system = head_object.modifiers.new(name='Fur', type='PARTICLE_SYSTEM')
particle_system.particle_system.settings.type = 'HAIR'
particle_system.particle_system.settings.hair_length = 1.0  # Set hair length
particle_system.particle_system.settings.count = 1000  # Adjust hair count

# Switch to Sculpt Mode to refine the facial features if needed
bpy.ops.object.mode_set(mode='SCULPT')
