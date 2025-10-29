for cam in cameras:
    scene.camera = cam["object"]
    scene.render.filepath = cam["filepath"]
    bpy.ops.render.render(write_still=True)
