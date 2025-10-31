"""
Blender Python Script: Complete Data Structure, Table Display and Export Framework
Compatible with Blender API v4

This script demonstrates the hierarchical data structure architecture of Blender
and provides table display and export functionality with file browser operations.
Includes comprehensive export capabilities and data management.
"""

import math
import os

import bpy
from mathutils import Vector

# Scene Initialization - Clean scene as requested
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


class BlenderFileDisplay:
    """
    Manages file display modes in Blender's file browser.
    Provides control over how files are displayed in the interface.
    """

    @staticmethod
    def set_display_mode(file_browser, mode='LIST_HORIZONTAL'):
        """
        Set the display mode for file browser.
        
        Args:
            file_browser: File browser space
            mode (str): Display mode - 'LIST_VERTICAL', 'LIST_HORIZONTAL', or 'THUMBNAIL'
        """
        if mode == 'LIST_VERTICAL':
            file_browser.params.display_type = 'LIST_VERTICAL'
        elif mode == 'LIST_HORIZONTAL':
            file_browser.params.display_type = 'LIST_HORIZONTAL'
        elif mode == 'THUMBNAIL':
            file_browser.params.display_type = 'THUMBNAIL'
        else:
            print(f"Unknown display mode: {mode}. Using LIST_HORIZONTAL.")
            file_browser.params.display_type = 'LIST_HORIZONTAL'

        print(f"File display mode set to: {mode}")

    @staticmethod
    def get_display_mode(file_browser):
        """Get current display mode."""
        mode = file_browser.params.display_type
        mode_map = {
            'LIST_VERTICAL': 'Short List',
            'LIST_HORIZONTAL': 'Long List',
            'THUMBNAIL': 'Thumbnails'
        }
        return mode_map.get(mode, 'Unknown')


class BlenderExportManager:
    """
    Comprehensive export manager for Blender scenes.
    Provides extensive export options including objects, collections, animations, and file formats.
    """

    def __init__(self, context=None):
        self.context = context if context else bpy.context
        self.scene = self.context.scene
        self.export_settings = {
            'format': 'glTF',
            'export_selected': False,
            'export_visible': False,
            'export_renderable': False,
            'export_collections': False,
            'export_animations': False,
            'custom_properties': False,
            'apply_modifiers': False,
            'frame_start': 1,
            'frame_end': 250,
            'transform_samples': 1,
            'geometry_samples': 1,
            'export_uvs': True,
            'export_normals': True,
            'export_colors': True,
            'export_yup': True
        }

    def configure_export(self, **kwargs):
        """
        Configure export settings.
        
        Args:
            **kwargs: Export configuration parameters
        """
        for key, value in kwargs.items():
            if key in self.export_settings:
                self.export_settings[key] = value
                print(f"Set {key} = {value}")
            else:
                print(f"Unknown export setting: {key}")

    def export_scene(self, filepath, file_format='glTF'):
        """
        Export the scene with current settings.
        
        Args:
            filepath (str): Output file path
            file_format (str): Export format ('glTF', 'FBX', 'OBJ', etc.)
            
        Returns:
            str: Export result message
        """
        try:
            # Configure export parameters based on settings
            export_params = {
                'filepath': filepath,
                'export_format': file_format,
                'export_selected': self.export_settings['export_selected'],
                'use_visible': self.export_settings['export_visible'],
                'use_renderable': self.export_settings['export_renderable'],
                'use_active_collection': self.export_settings['export_collections'],
                'export_animations': self.export_settings['export_animations'],
                'export_custom_properties': self.export_settings['custom_properties'],
                'export_apply': self.export_settings['apply_modifiers'],
                'export_yup': self.export_settings['export_yup'],
                'export_uvs': self.export_settings['export_uvs'],
                'export_normals': self.export_settings['export_normals'],
                'export_colors': self.export_settings['export_colors'],
                'export_frame_start': self.export_settings['frame_start'],
                'export_frame_end': self.export_settings['frame_end']
            }

            # Execute export based on format
            if file_format == 'glTF':
                bpy.ops.export_scene.gltf(**export_params)
            elif file_format == 'FBX':
                bpy.ops.export_scene.fbx(**export_params)
            elif file_format == 'OBJ':
                bpy.ops.export_scene.obj(**export_params)
            else:
                print(f"Unsupported export format: {file_format}")
                return f"Export failed: Unsupported format {file_format}"

            print(f"Scene exported successfully to: {filepath}")
            return f"Export successful: {filepath}"

        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            print(error_msg)
            return error_msg

    def export_object(self, obj, filepath, file_format='glTF'):
        """
        Export a specific object.
        
        Args:
            obj (Object): Object to export
            filepath (str): Output file path
            file_format (str): Export format
            
        Returns:
            str: Export result message
        """
        # Select only the target object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        self.context.view_layer.objects.active = obj

        # Temporarily modify settings for single object export
        original_settings = self.export_settings.copy()
        self.configure_export(export_selected=True)

        result = self.export_scene(filepath, file_format)

        # Restore original settings
        self.export_settings = original_settings

        return result

    def export_collection(self, collection, filepath, file_format='glTF', include_nested=True):
        """
        Export a collection of objects.
        
        Args:
            collection (Collection): Collection to export
            filepath (str): Output file path
            file_format (str): Export format
            include_nested (bool): Include nested collections
            
        Returns:
            str: Export result message
        """
        # Set collection export settings
        original_settings = self.export_settings.copy()
        self.configure_export(export_collections=True, export_selected=True)

        # Select all objects in collection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collection.all_objects:
            obj.select_set(True)

        if self.context.view_layer.objects:
            self.context.view_layer.objects.active = self.context.view_layer.objects[0]

        result = self.export_scene(filepath, file_format)

        # Restore original settings
        self.export_settings = original_settings

        return result


class BlenderDataManager:
    """
    Enhanced data manager that provides table-like operations using Blender's
    data-block system. This is a workaround for the lack of traditional table APIs.
    """

    def __init__(self):
        self.data = bpy.data
        self.scene = bpy.context.scene
        self.collection_name = "DataCollection"
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the data collection exists."""
        if self.collection_name not in self.data.collections:
            self.data.collections.new(self.collection_name)
        self.collection = self.data.collections[self.collection_name]

    def add_row(self, data_type="mesh", name_prefix="Item", properties=None):
        """
        Add a new data entry (analogous to adding a row in a table).
        
        Args:
            data_type (str): Type of data-block to create ('mesh', 'material', 'object', 'camera', 'light')
            name_prefix (str): Prefix for the name
            properties (dict): Additional properties to store
            
        Returns:
            dict: Created data entry with metadata
        """
        timestamp = len([obj for obj in self.data.objects if obj.name.startswith(name_prefix)])
        unique_name = f"{name_prefix}_{timestamp:03d}"

        if properties is None:
            properties = {}

        if data_type == "mesh":
            data_obj = self.data.meshes.new(unique_name)
        elif data_type == "material":
            data_obj = self.data.materials.new(unique_name)
            data_obj.use_nodes = True
        elif data_type == "object":
            data_obj = self.data.objects.new(unique_name, None)
        elif data_type == "camera":
            data_obj = self.data.cameras.new(unique_name)
        elif data_type == "light":
            data_obj = self.data.lights.new(unique_name, 'POINT')
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

        # Store custom properties (simulating table cell values)
        for key, value in properties.items():
            data_obj[key] = value

        entry = {
            'name': unique_name,
            'type': data_type,
            'data_block': data_obj,
            'properties': properties,
            'index': len(self.collection.objects)
        }

        print(f"Added row: {unique_name} ({data_type})")
        return entry

    def remove_row(self, entry):
        """
        Remove a data entry (analogous to removing a row from a table).
        
        Args:
            entry (dict): Entry to remove (returned by add_row)
        """
        data_block = entry['data_block']
        data_type = entry['type']

        try:
            if data_type == "mesh":
                self.data.meshes.remove(data_block)
            elif data_type == "material":
                self.data.materials.remove(data_block)
            elif data_type == "object":
                self.data.objects.remove(data_block)
            elif data_type == "camera":
                self.data.cameras.remove(data_block)
            elif data_type == "light":
                self.data.lights.remove(data_block)

            print(f"Removed row: {entry['name']}")
        except Exception as e:
            print(f"Error removing row {entry['name']}: {e}")

    def update_data(self, entry, new_properties):
        """
        Update data properties (analogous to updating table cell values).
        
        Args:
            entry (dict): Entry to update
            new_properties (dict): New property values
        """
        data_block = entry['data_block']

        # Update properties with read-only check
        for key, value in new_properties.items():
            if hasattr(data_block, key):
                # Check if the property is read-only before attempting to set it
                if key == "name":
                    # Special handling for name
                    old_name = data_block.name
                    data_block.name = value
                    entry['name'] = value
                    print(f"Renamed {old_name} to {value}")
                elif not data_block.is_property_readonly(key):
                    setattr(data_block, key, value)
                    print(f"Updated {key} to {value} for {entry['name']}")
                else:
                    print(f"Skipped read-only property: {key} for {entry['name']}")
            else:
                # For properties that don't exist as direct attributes, 
                # store as custom properties
                data_block[key] = value
                print(f"Set custom property {key} to {value} for {entry['name']}")

        # Update stored properties (always update the custom properties dict)
        entry['properties'].update(new_properties)

    def get_all_entries(self):
        """Get all entries in the data collection."""
        entries = []
        for data_block in self.data.meshes:
            if data_block.name.startswith("Item_"):
                entries.append({'name': data_block.name, 'type': 'mesh', 'data_block': data_block})
        for data_block in self.data.materials:
            if data_block.name.startswith("Item_"):
                entries.append({'name': data_block.name, 'type': 'material', 'data_block': data_block})
        for data_block in self.data.objects:
            if data_block.name.startswith("Item_"):
                entries.append({'name': data_block.name, 'type': 'object', 'data_block': data_block})
        for data_block in self.data.cameras:
            if data_block.name.startswith("Item_"):
                entries.append({'name': data_block.name, 'type': 'camera', 'data_block': data_block})
        for data_block in self.data.lights:
            if data_block.name.startswith("Item_"):
                entries.append({'name': data_block.name, 'type': 'light', 'data_block': data_block})

        return entries

    def display_table(self):
        """Display current data in a table-like format."""
        entries = self.get_all_entries()
        print("\n=== Data Table View ===")
        print(f"{'Index':<6} {'Name':<20} {'Type':<10} {'Properties'}")
        print("-" * 70)
        for i, entry in enumerate(entries):
            props_str = str(entry['properties'])[:40] + "..." if len(str(entry['properties'])) > 40 else str(
                entry['properties'])
            print(f"{i:<6} {entry['name']:<20} {entry['type']:<10} {props_str}")
        print("=" * 70)


class BlenderDataStructure:
    """
    Represents the Blender data structure architecture following the ID -> BlendData pattern.
    """

    def __init__(self):
        self.bpy_data = bpy.data
        self.structure_info = {
            'base_type': 'bpy_struct',
            'container_type': 'BlendData',
            'data_block_types': [
                'Action', 'Armature', 'Brush', 'Camera', 'Collection',
                'Curve', 'Image', 'Material', 'Mesh', 'Object',
                'Scene', 'Sound', 'Texture'
            ],
            'collections': {
                'actions': 'Collection of Action data-blocks',
                'armatures': 'Collection of Armature data-blocks',
                'brushes': 'Collection of Brush data-blocks',
                'cameras': 'Collection of Camera data-blocks',
                'collections': 'Collection of Collection data-blocks',
                'curves': 'Collection of Curve data-blocks',
                'images': 'Collection of Image data-blocks',
                'materials': 'Collection of Material data-blocks',
                'meshes': 'Collection of Mesh data-blocks',
                'objects': 'Collection of Object data-blocks',
                'scenes': 'Collection of Scene data-blocks',
                'sounds': 'Collection of Sound data-blocks',
                'textures': 'Collection of Texture data-blocks'
            }
        }

    def analyze_structure(self):
        """Analyze and display the current Blender data structure."""
        print("=== Blender Data Structure Analysis ===")
        print(f"Base Type: {self.structure_info['base_type']}")
        print(f"Container Type: {self.structure_info['container_type']}")
        print("\nData Block Types:")
        for dtype in self.structure_info['data_block_types']:
            print(f"  - {dtype}")

        print("\nCollection Counts:")
        for collection_name, description in self.structure_info['collections'].items():
            if hasattr(self.bpy_data, collection_name):
                collection = getattr(self.bpy_data, collection_name)
                count = len(collection)
                print(f"  - {collection_name}: {count} items ({description})")

        print("=" * 50)


class DataBlockManager:
    """
    Manages individual data-blocks following the ID class pattern.
    """

    def __init__(self):
        self.data = bpy.data

    def create_material(self, name="CustomMaterial", base_color=(0.8, 0.3, 0.1, 1.0),
                        roughness=0.5, metallic=0.0):
        """
        Create a material following the ID data-block pattern.
        
        Args:
            name (str): Material name
            base_color (tuple): RGBA color values
            roughness (float): Surface roughness (0.0-1.0)
            metallic (float): Metallic factor (0.0-1.0)
            
        Returns:
            Material: Created material data-block
        """
        material = self.data.materials.new(name)
        material.use_nodes = True

        # Get the Principled BSDF shader
        nodes = material.node_tree.nodes
        principled = nodes.get("Principled BSDF")

        if principled:
            principled.inputs["Base Color"].default_value = base_color
            principled.inputs["Roughness"].default_value = roughness
            principled.inputs["Metallic"].default_value = metallic

        return material


def clean_scene():
    """
    Clean the current scene by removing all objects and data-blocks.
    This function ensures a fresh start for the 3D modeling process.
    """
    # Remove all objects from the scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Remove unused data-blocks to prevent memory bloat
    # Clean meshes
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    # Clean materials
    for material in bpy.data.materials:
        if material.users == 0:
            bpy.data.materials.remove(material)

    # Clean images
    for image in bpy.data.images:
        if image.users == 0:
            bpy.data.images.remove(image)

    # Clean lights
    for light in bpy.data.lights:
        if light.users == 0:
            bpy.data.lights.remove(light)

    # Clean cameras
    for camera in bpy.data.cameras:
        if camera.users == 0:
            bpy.data.cameras.remove(camera)

    print("Scene cleaned successfully")


def create_model():
    """
    Create a 3D model with proper data structure implementation.
    
    Returns:
        Object: The created model object
    """
    # Create a new mesh data-block
    mesh_data = bpy.data.meshes.new("ProceduralModelMesh")

    # Create basic mesh geometry (icosphere)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0, location=(0, 0, 0))
    icosphere = bpy.context.active_object

    # Assign the mesh data to the object
    icosphere.data = mesh_data

    # Apply smooth shading
    bpy.ops.object.shade_smooth()

    # Center the model at origin (already at origin, but ensure)
    icosphere.location = (0, 0, 0)

    # Create and assign material
    material_manager = DataBlockManager()
    material = material_manager.create_material(
        name="ProceduralMaterial",
        base_color=(0.2, 0.6, 0.9, 1.0),
        roughness=0.3,
        metallic=0.1
    )

    apply_material(icosphere, material)

    print(f"Model created: {icosphere.name}")
    return icosphere


def apply_material(obj, material):
    """
    Apply material to an object following Blender's data-block assignment pattern.
    
    Args:
        obj (Object): Target object
        material (Material): Material data-block to apply
    """
    if obj.data is not None:
        if hasattr(obj.data, 'materials'):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(material)
            else:
                obj.data.materials[0] = material

    print(f"Material applied to {obj.name}")


def setup_lighting():
    """
    Create a 3-point lighting system with area lights for soft shadows.
    
    Returns:
        dict: Dictionary containing the created lights
    """
    lights = {}

    # Key Light - Main strong light
    bpy.ops.object.light_add(type='AREA', location=(5, 5, 8))
    key_light = bpy.context.active_object
    key_light.name = "KeyLight"
    key_light.data.energy = 1000
    key_light.data.size = 3
    lights['key'] = key_light

    # Fill Light - Softer light to reduce shadows
    bpy.ops.object.light_add(type='AREA', location=(-4, 2, 5))
    fill_light = bpy.context.active_object
    fill_light.name = "FillLight"
    fill_light.data.energy = 500
    fill_light.data.size = 4
    lights['fill'] = fill_light

    # Back/Rim Light - Adds depth and separation
    bpy.ops.object.light_add(type='AREA', location=(0, -6, 7))
    back_light = bpy.context.active_object
    back_light.name = "BackLight"
    back_light.data.energy = 800
    back_light.data.size = 2
    lights['back'] = back_light

    print("3-point lighting system created")
    return lights


def setup_camera():
    """
    Set up a wide-angle camera with adjustable parameters.
    
    Returns:
        Camera: The created camera object
    """
    # Create camera
    bpy.ops.object.camera_add(location=(8, -8, 6))
    camera = bpy.context.active_object
    camera.name = "MainCamera"

    # Set wide angle with approximately 180 degree FOV
    camera.data.lens = 8  # Wide angle lens

    # Point camera towards origin
    direction = Vector((0, 0, 1)) - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    print(f"Camera setup: FOV ~{camera.data.angle * 180 / math.pi:.1f} degrees")
    return camera


def render_views(obj, cam, output_dir="//renders", angles=None):
    """
    Render multiple views of the object using the established camera.
    
    Args:
        obj (Object): Object to render
        cam (Camera): Camera to use for rendering
        output_dir (str): Output directory for renders
        angles (list): List of angles to render from
        
    Returns:
        list: List of render file paths
    """
    if angles is None:
        angles = [0, 45, 90, 135, 180, 225, 270, 315]  # Full circle in 45-degree increments

    render_paths = []

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Set render settings
    bpy.context.scene.render.filepath = os.path.join(output_dir, "render_")

    for i, angle in enumerate(angles):
        # Calculate camera position around the object
        radius = 10
        x = radius * math.cos(math.radians(angle))
        y = radius * math.sin(math.radians(angle))
        z = 6

        # Update camera position
        cam.location = (x, y, z)

        # Point camera at object
        direction = obj.location - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        # Render
        render_path = os.path.join(output_dir, f"render_{i:03d}_{angle}deg.png")
        bpy.context.scene.render.filepath = render_path
        bpy.ops.render.render(write_still=True)

        render_paths.append(render_path)
        print(f"Rendered view {i + 1}/{len(angles)}: {angle}°")

    print(f"All renders completed. Output directory: {output_dir}")
    return render_paths


def demonstrate_table_operations():
    """
    Demonstrate table-like operations using Blender's data-block system.
    This addresses the core table operations requirement using Blender's native architecture.
    """
    print("\n=== Demonstrating Table Operations ===")
    data_manager = BlenderDataManager()

    # Add rows (create data-blocks)
    print("\n1. Adding rows (creating data entries):")
    entry1 = data_manager.add_row("material", "Material", {"color": [1.0, 0.0, 0.0, 1.0], "roughness": 0.5})
    entry2 = data_manager.add_row("mesh", "Mesh", {"vertex_count": 100, "face_count": 200})
    entry3 = data_manager.add_row("object", "Object", {"location": [1, 2, 3], "scale": 1.5})

    # Display current table
    data_manager.display_table()

    # Update data (modify properties)
    print("\n2. Updating data (modifying properties):")
    data_manager.update_data(entry1, {"roughness": 0.8, "metallic": 0.2})
    data_manager.update_data(entry2, {"vertex_count": 150, "face_count": 250})

    # Display updated table
    data_manager.display_table()

    # Remove row (delete data-block)
    print("\n3. Removing row (deleting data entry):")
    data_manager.remove_row(entry2)

    # Final table display
    data_manager.display_table()

    print("\nTable operations demonstration complete!")
    return data_manager


def demonstrate_export_functionality():
    """
    Demonstrate the export functionality with various options.
    """
    print("\n=== Demonstrating Export Functionality ===")

    export_manager = BlenderExportManager()

    # Configure export settings for different scenarios
    print("\n1. Configuring export settings:")
    export_manager.configure_export(
        export_selected=True,
        export_uvs=True,
        export_normals=True,
        export_colors=True,
        custom_properties=True,
        apply_modifiers=True,
        transform_samples=5,
        geometry_samples=10,
        frame_start=1,
        frame_end=100
    )

    # Export scene with default settings
    print("\n2. Exporting full scene to GLTF:")
    result1 = export_manager.export_scene("//exports/scene_export.gltf", "glTF")
    print(result1)

    # Export with different format
    print("\n3. Exporting scene to FBX:")
    result2 = export_manager.export_scene("//exports/scene_export.fbx", "FBX")
    print(result2)

    return export_manager


def main():
    """
    Main function to orchestrate the entire process.
    Demonstrates the data structure architecture, table operations, export functionality, and creates a complete 3D scene.
    """
    print("Starting Blender Complete Data Structure and Export Framework...")

    # Analyze Blender's data structure
    data_structure = BlenderDataStructure()
    data_structure.analyze_structure()

    # Initialize scene
    clean_scene()

    # Demonstrate table operations using Blender's system
    data_manager = demonstrate_table_operations()

    # Demonstrate export functionality
    export_manager = demonstrate_export_functionality()

    # Create 3D model
    model = create_model()

    # Setup lighting
    lights = setup_lighting()

    # Setup camera
    camera = setup_camera()

    # Render multiple views (comment out if you don't want to render)
    # render_paths = render_views(model, camera, save_dir)

    print("\nScene setup complete!")
    print(f"Model: {model.name}")
    print(f"Lights: {list(lights.keys())}")
    print(f"Camera: {camera.name}")
    print(f"Data entries: {len(data_manager.get_all_entries())}")
    print("Export and table operations demonstration completed!")

if __name__ == "__main__":
    # Placeholder for render output directory
    save_dir = "//renders"  # Relative to .blend file directory

    # Run the main function
    main()

import json as js

import bpy

camera_template_file = 'templates/camera_templates/template.json'
save_dir = "assets/rendered_images/critic/0"

with open(camera_template_file, 'r') as f:
    camera_data = js.load(f)

# Scene
scene = bpy.context.scene

scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1024

cameras = []
for data in camera_data:
    # Create camera data block
    cam_data = bpy.data.cameras.new(name=data["name"])

    # cam_data.type = 'ORTHO'
    # cam_data.ortho_scale = 8.0  # giá trị càng nhỏ → zoom càng gần

    # Create camera object
    cam_object = bpy.data.objects.new(data["name"], cam_data)

    # Set position and rotation
    cam_object.location = data["location"]
    cam_object.rotation_euler = data["rotation_euler"]

    # Link to Scene Collection
    bpy.context.collection.objects.link(cam_object)

    # Save object and file path
    cameras.append({
        "object": cam_object,
        "filepath": data["filepath"].format(save_dir=save_dir)
    })

for cam in cameras:
    scene.camera = cam["object"]
    scene.render.filepath = cam["filepath"]
    bpy.ops.render.render(write_still=True)
