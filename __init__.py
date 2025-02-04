'''
Copyright (C) 2025 Wayne Dixon
wayen@cgcookie.com
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


bl_info = {
    "name": "Apply modifier with shape keys",
    "author": "Wayne Dixon", 
    "blender": (4, 3, 2),
    "version": (0, 0, 1),
    "location": "Shape Key Specials Menu",
    "description": "Apply modifiers on mesh with shape keys (Avoids the error 'Modifier cannot be applied to a mesh with shape keys').",
    "category": "Object"
}


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

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.MESH_MT_shape_key_context_menu.append(menu_func)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    bpy.types.MESH_MT_shape_key_context_menu.remove(menu_func)


if __name__ == "__main__":
    register()