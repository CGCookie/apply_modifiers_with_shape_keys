'''
Copyright (C) 2025 Wayne Dixon
wayen@cgcookie.com
Created by Wayne Dixon
    This file is part of Apply Modifiers With Shape Keys.
    It is free software; you can redistribute it and/or
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
from .apply_modifiers_with_shape_keys import ModifierList, OBJECT_OT_apply_modifiers_with_shape_keys


# Register and unregister classes
def menu_func(self, context):
    self.layout.separator()  # Add a separator before the operator for a cleaner look
    self.layout.operator(OBJECT_OT_apply_modifiers_with_shape_keys.bl_idname)


classes = [
    ModifierList,
    OBJECT_OT_apply_modifiers_with_shape_keys,
]


def menu_func_global(self, context):
    self.layout.operator(OBJECT_OT_apply_modifiers_with_shape_keys.bl_idname)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.MESH_MT_shape_key_context_menu.append(menu_func)
    # force it to show in the F3 menu
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.types.MESH_MT_shape_key_context_menu.remove(menu_func)
    for cls in classes:
        bpy.utils.unregister_class(cls)
