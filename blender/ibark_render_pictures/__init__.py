bl_info = {
    "name": "iBark Batch Shot",
    "author": "István / iBarkGames",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "3D View > N-panel > iBark > Batch Shot",
    "category": "Render",
    "description": "Render selected (or chosen) cameras at multiple resolutions. Filenames: {datetime}_{blendname}_{resolution}.png",
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import (
    StringProperty, BoolProperty, EnumProperty,
)
from datetime import datetime
import os
import re

# --- Helpers ---------------------------------------------------------------

def safe_blend_basename():
    p = bpy.data.filepath
    return os.path.splitext(os.path.basename(p))[0] if p else "unsaved"

def parse_res_list(text: str):
    """
    Accepts: '3840x2160, 1920x1080' OR '3840-2160,1920-1080'
    Returns list of (w, h, "WxH")
    """
    if not text.strip():
        return []
    parts = re.split(r"[,\s]+", text.strip())
    out = []
    for p in parts:
        m = re.match(r"^\s*(\d+)\s*[xX\-]\s*(\d+)\s*$", p)
        if not m:
            continue
        w, h = int(m.group(1)), int(m.group(2))
        if w > 0 and h > 0:
            out.append((w, h, f"{w}x{h}"))
    return out

def derive_ig_variants(w, h):
    """
    Based on the base res:
    - IG Square:   min x min
    - IG Portrait: 4:5 (width=min, height=round(min*5/4))
    - IG Landscape: 1.91:1 (height=min, width=round(min*1.91))
    Returns list of (w, h, tag)
    """
    s = min(w, h)
    sq = (s, s, f"{s}x{s}_igSquare")
    port_h = round(s * 5 / 4)
    port = (s, port_h, f"{s}x{port_h}_igPortrait")
    land_w = round(s * 1.91)
    land = (land_w, s, f"{land_w}x{s}_igLandscape")
    return [sq, port, land]

def camera_enum_items(self, context):
    items = []
    for cam in [o for o in bpy.data.objects if o.type == 'CAMERA']:
        items.append((cam.name, cam.name, "", 0))
    return items or [("","<no cameras>","",0)]

# --- Properties stored on the Scene so the UI remembers -------------------

def ensure_props():
    sc = bpy.types.Scene
    if not hasattr(sc, "ibark_output_dir"):
        sc.ibark_output_dir = StringProperty(
            name="Output Directory",
            subtype='DIR_PATH',
            description="Where to write renders (can be your local Dropbox path)",
            default="//renders/"
        )
    if not hasattr(sc, "ibark_resolutions"):
        sc.ibark_resolutions = StringProperty(
            name="Resolutions",
            description="Comma-separated list, e.g. 3840x2160, 1920x1080",
            default="3840x2160, 1920x1080"
        )
    if not hasattr(sc, "ibark_use_selected"):
        sc.ibark_use_selected = BoolProperty(
            name="Use Selected Cameras",
            description="If enabled, use currently selected camera objects. Otherwise use the list below.",
            default=True
        )
    if not hasattr(sc, "ibark_cameras"):
        sc.ibark_cameras = EnumProperty(
            name="Cameras",
            description="Choose one or more cameras when not using selection",
            items=camera_enum_items,
            options={'ENUM_FLAG'}
        )
    if not hasattr(sc, "ibark_add_ig"):
        sc.ibark_add_ig = BoolProperty(
            name="Add Instagram variants",
            description="Also render Square (1:1), Portrait (4:5), Landscape (1.91:1) based on each base resolution",
            default=True
        )

ensure_props()

# --- Operator --------------------------------------------------------------

class IBARK_OT_batch_render(Operator):
    bl_idname = "ibark.batch_render"
    bl_label = "Boom! Generate Shots"
    bl_options = {"REGISTER", "UNDO"}

    def _gather_cameras(self, context):
        scn = context.scene
        cams = []
        if scn.ibark_use_selected:
            cams = [o for o in context.selected_objects if o.type == 'CAMERA']
        else:
            chosen = set(scn.ibark_cameras)
            cams = [bpy.data.objects[n] for n in chosen if n in bpy.data.objects and bpy.data.objects[n].type=='CAMERA']
        # Fallback: active camera if nothing chosen
        if not cams and context.scene.camera:
            cams = [context.scene.camera]
        return cams

    def execute(self, context):
        scn = context.scene
        out_dir = bpy.path.abspath(scn.ibark_output_dir)
        os.makedirs(out_dir, exist_ok=True)

        cams = self._gather_cameras(context)
        if not cams:
            self.report({'ERROR'}, "No cameras found/selected.")
            return {'CANCELLED'}

        bases = parse_res_list(scn.ibark_resolutions)
        if not bases:
            self.report({'ERROR'}, "No valid resolutions. Use e.g. 3840x2160,1920x1080")
            return {'CANCELLED'}

        # Save & restore key render settings
        r = scn.render
        orig_cam = scn.camera
        orig_x, orig_y = r.resolution_x, r.resolution_y
        orig_pct = r.resolution_percentage
        orig_path = r.filepath
        orig_fmt = r.image_settings.file_format

        blendname = safe_blend_basename()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        try:
            r.image_settings.file_format = 'PNG'
            r.resolution_percentage = 100

            for cam in cams:
                scn.camera = cam

                variants = []
                for (w, h, tag) in bases:
                    variants.append((w, h, tag))
                    if scn.ibark_add_ig:
                        variants.extend(derive_ig_variants(w, h))

                # remove duplicates while preserving order
                seen = set()
                uniq = []
                for w,h,tag in variants:
                    key = (w,h,tag)
                    if key not in seen:
                        uniq.append((w,h,tag))
                        seen.add(key)

                for (w, h, tag) in uniq:
                    r.resolution_x, r.resolution_y = w, h
                    res_str = f"{w}x{h}" if "_ig" not in tag else tag  # include IG tag in name
                    fname = f"{stamp}_{blendname}_{res_str}_{cam.name}.png"
                    r.filepath = os.path.join(out_dir, fname)
                    # Render still with current engine/settings
                    bpy.ops.render.render(write_still=True)
                    self.report({'INFO'}, f"Saved: {r.filepath}")

        finally:
            # Restore
            scn.camera = orig_cam
            r.resolution_x, r.resolution_y = orig_x, orig_y
            r.resolution_percentage = orig_pct
            r.filepath = orig_path
            r.image_settings.file_format = orig_fmt

        return {'FINISHED'}

# --- UI Panel --------------------------------------------------------------

class IBARK_PT_batch_panel(Panel):
    bl_label = "Batch Shot"
    bl_idname = "IBARK_PT_batch_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "iBark"

    def draw(self, context):
        scn = context.scene
        col = self.layout.column(align=True)
        col.prop(scn, "ibark_output_dir")
        col.prop(scn, "ibark_resolutions")
        col.separator()
        col.prop(scn, "ibark_use_selected")
        if not scn.ibark_use_selected:
            col.prop(scn, "ibark_cameras")
        col.prop(scn, "ibark_add_ig")
        col.separator()
        col.operator("ibark.batch_render", icon="RENDER_STILL")

# --- Register --------------------------------------------------------------

classes = (IBARK_OT_batch_render, IBARK_PT_batch_panel)

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
