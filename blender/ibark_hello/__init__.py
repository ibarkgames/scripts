bl_info = {
    "name": "iBark Hello",
    "author": "István",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "F3: Hello (iBark) • Object > iBark > Hello",
    "category": "Object",
    "description": "Shows 'Hello, World!' or 'Hello, <Name>!'",
}

import bpy

class IBARK_OT_hello(bpy.types.Operator):
    bl_idname = "ibark.hello"             # ✅ correct attribute name
    bl_label = "Hello (iBark)"
    bl_options = {"REGISTER", "UNDO"}

    name: bpy.props.StringProperty(
        name="Name",
        description="Leave empty to greet 'World'",
        default="",
        maxlen=64,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        target = self.name.strip() or "World"
        message = f"Hello, {target}!"
        self.report({'INFO'}, message)
        print(message)
        return {"FINISHED"}

def menu_func(self, context):
    self.layout.separator()
    self.layout.label(text="iBark")
    self.layout.operator(IBARK_OT_hello.bl_idname, text="Hello (iBark)")

classes = (IBARK_OT_hello,)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
