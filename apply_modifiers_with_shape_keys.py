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
import re

# Helper functions
def disable_armature_modifiers(context, selected_modifiers, disable_armatures):
    ''' if there is an armature modifier on the mesh, you can disable it so it doesn't affect the deformation
    it will be reset back after the add-on is finished '''
    disabled_armature_modifiers = []
    if disable_armatures:
        for modifier in context.object.modifiers:
            if modifier.type == 'ARMATURE' and modifier.show_viewport:
                if modifier.name not in selected_modifiers:
                    disabled_armature_modifiers.append(modifier)
                    modifier.show_viewport = False
    return disabled_armature_modifiers

def duplicate_object(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'}, TRANSFORM_OT_translate={"value": (0, 0, 0)})

def apply_modifier_to_object(context, obj, selected_modifiers):
    bpy.context.view_layer.objects.active = obj
    for modifier_name in selected_modifiers:
        modifier = obj.modifiers.get(modifier_name)
        if modifier and not modifier.show_viewport: # enables the modifier before trying to apply it
            modifier.show_viewport = True
        try:
            bpy.ops.object.modifier_apply(modifier=modifier_name)
        except RuntimeError:
            print(f"Skipping broken modifier: {modifier_name}")

def save_shape_key_properties(obj, properties):
    ''' This function will save the settings on the shape keys (min/max etc) '''
    properties_list = []
    for key_block in obj.data.shape_keys.key_blocks:
        if key_block.name == "Basis":
            continue
        properties_object = {p: getattr(key_block, p) for p in properties}
        properties_list.append(properties_object)
    return properties_list

def restore_shape_key_properties(obj, properties_list):
    ''' Restores the settings for each shape key (min/max etc) '''
    for idx, key_block in enumerate(obj.data.shape_keys.key_blocks):
        if key_block.name == "Basis":
            continue
        for prop, value in properties_list[idx - 1].items():
            setattr(key_block, prop, value)

def copy_shape_key_drivers(obj, shape_key_properties):
    ''' Copy drivers for shape key properties '''

    drivers = {}

    # Ensure the object has a shape keys animation data
    if not obj.data.shape_keys.animation_data:
        # print(f"No animation data found for {obj.name}.") # DEBUG
        return drivers

    # Loop through all the drivers in the shape keys animation data
    for driver in obj.data.shape_keys.animation_data.drivers:
        # Only consider drivers related to shape key properties
        shape_key_drivers = []

        # Extract the property name from the data_path
        data_path_parts = driver.data_path.split('.')
        if len(data_path_parts) > 1:
            property_name = data_path_parts[-1]  # The last part of the data path is the property name (e.g. 'value', 'slider_min', 'slider_max')
            
            if property_name not in shape_key_properties:
                continue  # Skip if the property isn't one we care about
            
            # Find the shape key name
            match = re.search(r'key_blocks\["(.*)"\]', driver.data_path)
            shape_key_name = match.group(1)

            # Create a dictionary for the driver data
            driver_data = {
                "driver": driver,
                "property": property_name 
            }
            
            # Append the driver data to the shape_key_drivers list
            shape_key_drivers.append(driver_data)

        if shape_key_drivers:
            drivers[shape_key_name] = shape_key_drivers

    return drivers

def restore_shape_key_drivers(obj, copy_obj,drivers, context):
    ''' Restore drivers for shape key properties '''

    if not obj.data.shape_keys.animation_data:
        obj.data.shape_keys.animation_data_create()

    for shape_key_name, shape_key_drivers in drivers.items():
        # Find the shape key block by name
        shape_key_block = obj.data.shape_keys.key_blocks.get(shape_key_name)
        if not shape_key_block:            
            continue

        for driver_data in shape_key_drivers:
            # Extract the fcurve and property
            source_fcurve = driver_data["driver"]
            property_name = driver_data["property"]

            # Add the driver to the shape key property
            try:
                # Remove any drivers or animation on the shape keys
                obj.data.shape_keys.animation_data_clear()

                new_driver = shape_key_block.driver_add(property_name)
               
                # set the type
                new_driver.driver.type = source_fcurve.driver.type

                # Copy the driver expression if it exists
                if source_fcurve.driver.expression:
                    new_driver.driver.expression = source_fcurve.driver.expression
                
                # Copy the driver variables
                for var in source_fcurve.driver.variables:
                    new_var = new_driver.driver.variables.new()
                    new_var.name = var.name
                    new_var.type = var.type

                    # Copy each target for the variable
                    for idx, target in enumerate(var.targets):
                        new_var.targets[idx].id_type = target.id_type
                        if target.id == copy_obj: # if the target is point to the copy object this should be changed to the orginal object
                            target.id = obj
                        new_var.targets[idx].id = target.id
                        new_var.targets[idx].data_path = target.data_path
                        new_var.targets[idx].bone_target = target.bone_target
                        new_var.targets[idx].transform_type = target.transform_type
                        new_var.targets[idx].transform_space = target.transform_space

                # print(f"Restored driver for {property_name} on shape key {shape_key_name}.")  #DEBUG

            except Exception as e:
                print(f"Failed to restore driver for {property_name} on shape key {shape_key_name}: {str(e)}")
                # self.report({'ERROR'}, f"Failed to restore driver for {property_name} on shape key {shape_key_name}: {str(e)}")

def copy_shape_key_animation(source_obj, target_obj):
    ''' Relink all shape key animations (keyframes) for all properties from one object to another '''
    
    # Ensure the source object has an action for shape keys
    if not source_obj.data.shape_keys.animation_data:
        # print(f"{source_obj.name} has no animation data for shape keys.")# DEBUG
        return
    
    if not source_obj.data.shape_keys.animation_data.action:
        # print(f"{source_obj.name} has no action for shape keys.") # DEBUG
        return
    
    # Link the existing action to the target object
    target_obj.data.shape_keys.animation_data_create()  # Create animation data for the target object if needed
    target_obj.data.shape_keys.animation_data.action = source_obj.data.shape_keys.animation_data.action
    
    # print(f"Shape key animations copied from {source_obj.name} to {target_obj.name}.") # DEBUG

def apply_modifiers_with_shape_keys(context, selected_modifiers, disable_armatures):
    ''' Apply the selected modifiers to the mesh even if it has shape keys '''
    original_obj = context.view_layer.objects.active
    shapes_count = len(original_obj.data.shape_keys.key_blocks) if original_obj.data.shape_keys else 0
    error_message = None

    if shapes_count == 0: # if there are no shape keys just apply the selected modifiers
        apply_modifier_to_object(context, original_obj, selected_modifiers)
        return True, None

    # Disable armatures if necessary
    disabled_armature_modifiers = disable_armature_modifiers(context, selected_modifiers, disable_armatures)

    # Save the pin option setting and active shape key index
    pin_setting = bpy.data.objects[original_obj.name].show_only_shape_key
    saved_active_shape_key_index = original_obj.active_shape_key_index

    # Duplicate the object
    duplicate_object(original_obj)
    copy_obj = context.view_layer.objects.active

    # Make the Original Object the active object
    context.view_layer.objects.active = original_obj
    
    # Save the shape key properties
    properties = ["name", "mute", "lock_shape", "value", "slider_min", "slider_max", "vertex_group", "relative_key"]
    shape_key_properties = save_shape_key_properties(original_obj, properties)

    # Copy drivers for shape keys (from the copy because the original ones will be gone in a moment)
    shape_key_drivers = copy_shape_key_drivers(copy_obj, properties)

    # Remove all shape keys and apply modifiers on the original
    bpy.ops.object.shape_key_remove(all=True)
    apply_modifier_to_object(context, original_obj, selected_modifiers)

    # Add a basis shape key back to the original object
    original_obj.shape_key_add(name='Basis',from_mix=False)

    # Loop over the original shape keys, create a temp mesh, apply single shape, apply modifers and merge back to the original (1 shape at a time)
    for i, shape_properties in enumerate(shape_key_properties):
        # Create a temp object
        context.view_layer.objects.active = copy_obj
        duplicate_object(copy_obj)
        temp_obj = bpy.context.active_object

        # Pin the shape we want
        bpy.data.objects[temp_obj.name].show_only_shape_key = True
        temp_obj.active_shape_key_index = i + 1
        shape_key_name = temp_obj.active_shape_key.name

        # Apply the shape key to freeze the mesh in that position, then apply the modifiers
        for window in context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    with context.temp_override(window=window, area=area):
                        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                        apply_modifier_to_object(context, temp_obj, selected_modifiers)
                    break

        # Verify the meshes have the same amount of verts
        if len(original_obj.data.vertices) != len(temp_obj.data.vertices):
            error_message = f"{shape_key_name} failed because the mesh no longer have the same amount of vertices after applying the modifiers."
            # Clean up the temp object and try to move on
            bpy.data.objects.remove(temp_obj)
            continue
            

        # Transfer the temp object as a shape back to orginal
        temp_obj.select_set(True)
        context.view_layer.objects.active = original_obj
        bpy.ops.object.join_shapes()

        # Restore shape key properties
        restore_shape_key_properties(original_obj, shape_key_properties)

        # Restore the drivers for this shape key
        restore_shape_key_drivers(original_obj, copy_obj, shape_key_drivers, context)

        # Clean up the temp object
        bpy.data.objects.remove(temp_obj)

    # Restore any shape key animation
    copy_shape_key_animation(copy_obj, original_obj)

    # Clean up the duplicate object
    bpy.data.objects.remove(copy_obj)

    # Re-enable armature modifiers
    if disable_armatures:
        for modifier in disabled_armature_modifiers:
            modifier.show_viewport = True

    # Restore the pin option setting and active shape key index
    bpy.data.objects[original_obj.name].show_only_shape_key = pin_setting
    original_obj.active_shape_key_index =  saved_active_shape_key_index

    # Make sure the original object is selected before finishing
    original_obj.select_set(True)

    # Report the error message if any
    if error_message:
        return False, error_message
    
    return True, None

# Property Collection
class ModifierList(bpy.types.PropertyGroup): 
    apply_modifier: bpy.props.BoolProperty(name="", default=False)


# Operator for applying modifiers
class OBJECT_OT_apply_modifiers_with_shape_keys(bpy.types.Operator):
    ''' Apply selected modifiers to mesh even if it has shape keys '''
    bl_idname = "object.apply_modifiers_with_shape_keys"
    bl_label = "Apply modifier(s) for mesh with shape keys"
    bl_options = {'REGISTER', 'UNDO'}

    disable_armatures: bpy.props.BoolProperty(name="Exclude armature deformation", default=True)
    collection_property: bpy.props.CollectionProperty(type=ModifierList)

    @classmethod
    def poll(cls, context):
        active_object = context.active_object
        # Check if the active object is a mesh, has shape keys, and is in Object mode
        return active_object and active_object.type == 'MESH' and active_object.data.shape_keys and context.object.mode == 'OBJECT'

    def execute(self, context):
        selected_modifiers = [o.name for o in self.collection_property if o.apply_modifier]
        if not selected_modifiers:
            self.report({'ERROR'}, 'No modifiers selected!')
            return {'FINISHED'}

        success, error_info = apply_modifiers_with_shape_keys(context, selected_modifiers, self.disable_armatures)
        if not success:
            self.report({'ERROR'}, error_info)

        return {'FINISHED'}

    def draw(self, context):
        show_armature_option = False
        self.layout.label(text="Select which modifier(s) to apply")
        box = self.layout.box()
        
        for prop in self.collection_property:
            box.prop(prop, "apply_modifier", text=prop.name)
            for modifier in context.object.modifiers:
                if modifier.type == 'ARMATURE' and modifier.show_viewport:
                    show_armature_option = True

        # only show this if there is an enabled armature modifier on the mesh
        if show_armature_option: 
            self.layout.separator() 
            self.layout.prop(self, "disable_armatures")

    def invoke(self, context, event):
        self.collection_property.clear()
        for modifier in context.object.modifiers:
            item = self.collection_property.add()
            item.name = modifier.name
            item.apply_modifier = False
        return context.window_manager.invoke_props_dialog(self)

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
