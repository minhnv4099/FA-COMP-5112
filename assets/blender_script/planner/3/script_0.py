import bpy

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


class MyTableLayout(bpy.types.Panel):
    bl_label = "Table Layout"
    bl_idname = "PT_TableLayout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout

        # Example of using row() for table layout
        row = layout.row()
        row.prop(context.scene, 'some_property')  # Replace with actual property

        # Example of using column() for vertical alignment
        col = layout.column()
        col.label(text="Table Header")
        col.prop(context.scene, 'another_property')  # Replace with actual property

        # Example of using grid_flow() for grid layout
        grid = layout.grid_flow(columns=2, even_columns=True)
        grid.operator('object.select_all')
        grid.operator('object.delete')


def register():
    bpy.utils.register_class(MyTableLayout)


def unregister():
    bpy.utils.unregister_class(MyTableLayout)


if __name__ == "__main__":
    register()
