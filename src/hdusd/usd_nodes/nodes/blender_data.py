# **********************************************************************
# Copyright 2020 Advanced Micro Devices, Inc
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ********************************************************************
import bpy

from pxr import UsdGeom, Tf

from .base_node import USDNode
from ...utils import usd as usd_utils
from ...export import object, material, world
from ...export.object import ObjectData, SUPPORTED_TYPES, sdf_name
from ...export.camera import CameraData
from ...viewport.usd_collection import USD_CAMERA


#
# COLLECTION MENU and OPERATORS
#
class HDUSD_USD_NODETREE_OP_blender_data_link_collection(bpy.types.Operator):
    """Link collection"""
    bl_idname = "hdusd.usd_nodetree_blender_data_link_collection"
    bl_label = ""

    collection_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        context.node.collection = bpy.data.collections[self.collection_name]
        return {"FINISHED"}


class HDUSD_USD_NODETREE_OP_blender_data_unlink_collection(bpy.types.Operator):
    """Unlink collection"""
    bl_idname = "hdusd.usd_nodetree_blender_data_unlink_collection"
    bl_label = ""

    def execute(self, context):
        context.node.collection = None
        return {"FINISHED"}


class HDUSD_USD_NODETREE_MT_blender_data_collection(bpy.types.Menu):
    bl_idname = "HDUSD_USD_NODETREE_MT_blender_data_collection"
    bl_label = "Object"

    def draw(self, context):
        layout = self.layout
        collections = bpy.data.collections

        for coll in collections:
            if coll.name == "USD NodeTree":
                continue

            row = layout.row()
            op = row.operator(HDUSD_USD_NODETREE_OP_blender_data_link_collection.bl_idname,
                              text=coll.name)
            op.collection_name = coll.name


#
# OBJECT MENU and OPERATORS
#
class HDUSD_USD_NODETREE_OP_blender_data_link_object(bpy.types.Operator):
    """Link object"""
    bl_idname = "hdusd.usd_nodetree_blender_data_link_object"
    bl_label = ""

    object_name: bpy.props.StringProperty(default="")

    def execute(self, context):
        context.node.object = bpy.data.objects[self.object_name]
        return {"FINISHED"}


class HDUSD_USD_NODETREE_OP_blender_data_unlink_object(bpy.types.Operator):
    """Unlink object"""
    bl_idname = "hdusd.usd_nodetree_blender_data_unlink_object"
    bl_label = ""

    def execute(self, context):
        context.node.object = None
        return {"FINISHED"}


class HDUSD_USD_NODETREE_MT_blender_data_object(bpy.types.Menu):
    bl_idname = "HDUSD_USD_NODETREE_MT_blender_data_object"
    bl_label = "Object"

    def draw(self, context):
        layout = self.layout
        objects = bpy.data.objects

        for obj in objects:
            if (obj.type == 'CAMERA' and obj.name == USD_CAMERA) or obj.hdusd.is_usd or obj.type not in SUPPORTED_TYPES:
                continue

            row = layout.row()
            op = row.operator(HDUSD_USD_NODETREE_OP_blender_data_link_object.bl_idname,
                              text=obj.name)
            op.object_name = obj.name


class HDUSD_USD_NODETREE_OP_blender_data_update_animation(bpy.types.Operator):
    """Click this button if animation was updated"""
    bl_idname = "hdusd.usd_nodetree_blender_data_update_animation"
    bl_label = "Update animation"

    def execute(self, context):
        context.node.reset(True)
        return {'FINISHED'}


class BlenderDataNode(USDNode):
    """Blender data to USD can export whole scene, one collection or object"""
    bl_idname = 'usd.BlenderDataNode'
    bl_label = "Blender Data"
    bl_icon = "SCENE_DATA"

    input_names = ()
    use_hard_reset = False

    def update_data(self, context):
        self.reset(True)

    def set_end_frame(self, value):
        self['end_frame'] = self.start_frame if value < self.start_frame else value

    def get_end_frame(self):
        return self.get('end_frame', 0)

    def update_start_frame(self, context):
        if self.start_frame > self.end_frame:
            self.end_frame = self.start_frame

        self.update_data(context)

    data: bpy.props.EnumProperty(
        name="Data",
        description="Blender Data to read",
        items=(('SCENE', "Scene", "Read entire scene"),
            ('COLLECTION', "Collection", "Read collection"),
            ('OBJECT', 'Object', "Read single object"),
        ),
        default='SCENE',
        update=update_data
    )
    collection: bpy.props.PointerProperty(
        type=bpy.types.Collection,
        name="Collection",
        description="",
        update=update_data
    )
    object: bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Object",
        description="",
        update=update_data
    )
    is_use_animation: bpy.props.BoolProperty(
        name="Use animation",
        description="Use animation",
        default=True,
        update=update_data
    )
    is_restrict_frames: bpy.props.BoolProperty(
        name="Set frames",
        description="Set frames to export",
        default=False,
        update=update_data
    )
    start_frame: bpy.props.IntProperty(
        name="Start frame",
        description="Start frame to export",
        default=0,
        update=update_start_frame
    )
    end_frame: bpy.props.IntProperty(
        name="End frame",
        description="End frame to export",
        default=0,
        set=set_end_frame, get=get_end_frame,
        update=update_data
    )

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, 'data')

        if self.data == 'COLLECTION':
            split = layout.row(align=True).split(factor=0.25)
            col = split.column()
            col.label(text="Collection")
            col = split.column()
            row = col.row(align=True)
            if self.collection:
                row.menu(HDUSD_USD_NODETREE_MT_blender_data_collection.bl_idname,
                         text=self.collection.name, icon='OUTLINER_COLLECTION')
                row.operator(HDUSD_USD_NODETREE_OP_blender_data_unlink_collection.bl_idname, icon='X')
            else:
                row.menu(HDUSD_USD_NODETREE_MT_blender_data_collection.bl_idname,
                         text=" ", icon='OUTLINER_COLLECTION')

        elif self.data == 'OBJECT':
            split = layout.row(align=True).split(factor=0.25)
            col = split.column()
            col.label(text="Object")
            col = split.column()
            row = col.row(align=True)
            if self.object:
                row.menu(HDUSD_USD_NODETREE_MT_blender_data_object.bl_idname,
                         text=self.object.name, icon='OBJECT_DATAMODE')
                row.operator(HDUSD_USD_NODETREE_OP_blender_data_unlink_object.bl_idname, icon='X')
            else:
                row.menu(HDUSD_USD_NODETREE_MT_blender_data_object.bl_idname,
                         text=" ", icon='OBJECT_DATAMODE')

        layout.prop(self, 'is_use_animation')

        if self.is_use_animation:
            layout.prop(self, 'is_restrict_frames')

        if self.is_use_animation and self.is_restrict_frames:
            row = layout.row(align=True)
            row.prop(self, 'start_frame')
            row.prop(self, 'end_frame')

        if self.is_use_animation:
            layout.operator(HDUSD_USD_NODETREE_OP_blender_data_update_animation.bl_idname, icon='FILE_REFRESH')

    def compute(self, **kwargs):
        depsgraph = bpy.context.evaluated_depsgraph_get()

        stage = self.cached_stage.create()
        UsdGeom.SetStageMetersPerUnit(stage, 1)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

        root_prim = stage.GetPseudoRoot()

        kwargs = {'scene': depsgraph.scene,
                  'is_use_animation': self.is_use_animation,
                  'is_restrict_frames': self.is_restrict_frames,
                  'start_frame': self.start_frame,
                  'end_frame': self.end_frame}

        if self.data == 'SCENE':
            for obj_data in ObjectData.depsgraph_objects(depsgraph):
                object.sync(root_prim, obj_data, **kwargs)

            if depsgraph.scene.world is not None:
                world.sync(root_prim, depsgraph.scene.world)

        elif self.data == 'COLLECTION':
            if not self.collection:
                return

            for obj_col in self.collection.objects:
                if obj_col.hdusd.is_usd or (obj_col.type == 'CAMERA' and obj_col.name == USD_CAMERA ):
                    continue

                object.sync(root_prim, ObjectData.from_object(
                    obj_col.evaluated_get(depsgraph)), **kwargs)

        elif self.data == 'OBJECT':
            if not self.object or self.object.hdusd.is_usd:
                return

            object.sync(root_prim, ObjectData.from_object(self.object.evaluated_get(depsgraph)),
                        **kwargs)

        return stage

    def depsgraph_update(self, depsgraph):
        # to prevent recursion we need to don't update node if we changed smth in Blender's animation
        if self.is_use_animation:
            return

        stage = self.cached_stage()
        if not stage:
            self.final_compute()
            return

        is_updated = False

        root_prim = stage.GetPseudoRoot()
        kwargs = {'scene': depsgraph.scene}

        for update in depsgraph.updates:
            if isinstance(update.id, bpy.types.Scene):
                scene = update.id
                world.sync_update(root_prim, scene.world)
                usd_utils.set_delegate_variant(root_prim.GetAllChildren(),
                                               scene.hdusd.viewport.delegate_name)

                continue

            if isinstance(update.id, bpy.types.Object):
                obj = update.id
                if obj.hdusd.is_usd or obj.type == 'EMPTY':
                    continue

                if obj.type == 'CAMERA' and obj.name == USD_CAMERA:
                    continue

                obj_data = ObjectData.from_object(obj)
                # checking if object has to be updated
                if self.data == 'COLLECTION':
                    if not self.collection or \
                            obj.name not in self.collection.objects:
                        continue

                elif self.data == 'OBJECT':
                    if not self.object or \
                            ObjectData.from_object(self.object).sdf_name != obj_data.sdf_name:
                        continue

                # we need this "if" to prevent emergence of instancer object when we edit parent object
                if not obj.parent:
                    object.sync_update(root_prim, obj_data,
                                       update.is_updated_geometry, update.is_updated_transform,
                                       **kwargs)

                for inst_obj_data in ObjectData.depsgraph_objects_inst(depsgraph):
                    if obj_data.sdf_name == sdf_name(inst_obj_data.object):
                        object.sync_update(root_prim, inst_obj_data, update.is_updated_geometry, update.is_updated_transform
                                           , **kwargs)

                is_updated = True
                continue

            if isinstance(update.id, bpy.types.World):
                if self.data != 'SCENE':
                    continue

                wld = update.id
                world.sync_update(root_prim, wld)

                is_updated = True
                continue

            if isinstance(update.id, bpy.types.Collection):
                coll = update.id

                current_keys = set(prim.GetName() for prim in root_prim.GetAllChildren())
                required_keys = set()
                depsgraph_keys = set(obj_data.sdf_name for obj_data in ObjectData.depsgraph_objects(depsgraph))
                instances_keys = set(obj_data.sdf_name for obj_data in ObjectData.depsgraph_objects_inst(depsgraph))

                if self.data == 'SCENE':
                    required_keys = depsgraph_keys

                elif self.data == 'COLLECTION':
                    if not self.collection:
                        continue

                    if coll.name != self.collection.name:
                        continue

                    required_keys = set(object.sdf_name(obj) for obj in coll.objects)
                    required_keys.intersection_update(depsgraph_keys)
                    required_keys = required_keys | instances_keys

                elif self.data == 'OBJECT':
                    if not self.object:
                        continue

                    if object.sdf_name(self.object) in depsgraph_keys:
                        required_keys = {object.sdf_name(self.object)}

                keys_to_remove = current_keys - required_keys
                keys_to_add = required_keys - current_keys

                if keys_to_remove:
                    for key in keys_to_remove:
                        if key == world.OBJ_PRIM_NAME:
                            continue

                        root_prim.GetStage().RemovePrim(root_prim.GetPath().AppendChild(key))
                        is_updated = True

                if keys_to_add:
                    for obj_data in ObjectData.depsgraph_objects(depsgraph):
                        if obj_data.sdf_name not in keys_to_add:
                            continue

                        object.sync(root_prim, obj_data, **kwargs)
                        is_updated = True

                continue

        if is_updated:
            self.hdusd.usd_list.update_items()
            self._reset_next(True)

    def frame_change(self, depsgraph):
        super().frame_change(depsgraph)

        scene = depsgraph.scene
        data_source = scene.hdusd.viewport.data_source
        viewport_camera = scene.objects.get(USD_CAMERA, None)

        if not data_source:
            if viewport_camera:
                bpy.data.objects.remove(viewport_camera)
            return

        output_node = bpy.data.node_groups[data_source].get_output_node()
        if not output_node:
            return

        stage = output_node.cached_stage()
        if not stage:
            return

        nodetree_camera = scene.hdusd.viewport.nodetree_camera
        camera_prim = stage.GetPrimAtPath(nodetree_camera)
        if not camera_prim:
            if viewport_camera:
                bpy.data.objects.remove(viewport_camera)
            return

        for update in depsgraph.updates:
            if isinstance(update.id, bpy.types.Object) and isinstance(update.id.data, bpy.types.Camera):
                nodetree_camera_path = f"/{Tf.MakeValidIdentifier(update.id.name_full)}/" \
                                       f"{Tf.MakeValidIdentifier(update.id.data.name_full)}"

                if nodetree_camera == nodetree_camera_path:
                    camera_prim = stage.GetPrimAtPath(nodetree_camera)
                    camera_settings = CameraData.init_from_usd_camera(camera_prim)
                    viewport_camera = scene.objects.get(USD_CAMERA, None)

                    camera_settings.export_to_camera(viewport_camera)

                    return

    def material_update(self, mat):
        stage = self.cached_stage()
        material.sync_update_all(stage.GetPseudoRoot(), mat)
