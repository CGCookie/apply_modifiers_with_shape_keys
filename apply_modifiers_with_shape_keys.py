'''
Copyright (C) 2025 Wayne Dixon
wayne@cgcookie.com

Created by Wayne Dixon

    This file is part of Apply modifier with shape keys

    Export to .blend is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, see <https://www.gnu.org/licenses/>.

'''

import bpy

# Local imports
from .functions import apply_modifiers_with_shape_keys


# Property Collection
class ModifierList(bpy.types.PropertyGroup): 
    apply_modifier: bpy.props.BoolProperty(name="", default=False)


# Operator for applying modifiers
class OBJECT_OT_apply_modifiers_with_shape_keys(bpy.types.Operator):
    ''' Apply selected modifiers to mesh even if it has shape keys '''
    bl_idname = "object.apply_modifiers_with_shape_keys"
    bl_label = "Apply Modifier(s) for Mesh with Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    collection_property: bpy.props.CollectionProperty(type=ModifierList)

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        # Check if the active object is a mesh, has shape keys, and is in Object mode
        return active_object and active_object.data.shape_keys and context.object.mode == 'OBJECT'

    def execute(self, context):
        selected_modifiers = [o.name for o in self.collection_property if o.apply_modifier]
        if not selected_modifiers:
            self.report({'ERROR'}, 'No modifiers selected!')
            return {'FINISHED'}

        success, error_info = apply_modifiers_with_shape_keys(context, selected_modifiers)
        if not success:
            self.report({'ERROR'}, error_info)

        return {'FINISHED'}

    def draw(self, context):
        show_armature_option = False
        self.layout.label(text="Select which modifier(s) to apply")
        box = self.layout.box()
        
        for prop in self.collection_property:
            box.prop(prop, "apply_modifier", text=prop.name)


    def invoke(self, context, event):
        self.collection_property.clear()
        for modifier in context.object.modifiers:
            item = self.collection_property.add()
            item.name = modifier.name
            item.apply_modifier = False
        return context.window_manager.invoke_props_dialog(self)