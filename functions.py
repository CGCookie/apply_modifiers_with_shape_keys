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


import bpy
import re


# Helper functions
def disable_modifiers(context, selected_modifiers):
    ''' disables any modifiers that are not selected so the mesh can be calculated.
    Returns a list of modifiers it changed so they can be reset later '''
    saved_enabled_modifiers = []

    for modifier in context.object.modifiers:
        if modifier.name not in selected_modifiers and modifier.show_viewport:
            saved_enabled_modifiers.append(modifier)
            modifier.show_viewport = False
    return saved_enabled_modifiers


def duplicate_object(obj):
    '''Copy the object, make it active and return it '''
    new_obj = obj.copy()
    new_obj.data = obj.data.copy()
    bpy.context.collection.objects.link(new_obj)
    bpy.context.view_layer.objects.active = new_obj
    return new_obj


def evaluate_mesh(context, obj):
    """Low-level alternative to `bpy.ops.object.convert` for converting to meshes"""
    depsgraph = context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(eval_obj, preserve_all_data_layers=True, depsgraph=depsgraph)
    return mesh


def apply_modifier_to_object(context, obj, selected_modifiers):
    ''' Disables all modifers except the selected ones
    Creates a new mesh from that output and swaps it out
    Removes the selected modifiers
    Deletes the old mesh and restores the other modifiers to what they were
    '''
    context.view_layer.objects.active = obj

    # Disable all modifiers (except selected)
    saved_enabled_modifiers = disable_modifiers(context, selected_modifiers)

    # Make sure all selected modifers are enabled
    for modifier_name in selected_modifiers:
        modifier = obj.modifiers.get(modifier_name)
        modifier.show_viewport = True

    # evaluate new mesh and swap it out
    new_mesh = evaluate_mesh(context, obj)
    old_mesh = obj.data
    old_mesh_name = old_mesh.name
    obj.data = new_mesh

    # Delete the selected modifiers from the object
    for modifier in selected_modifiers:
        obj.modifiers.remove(obj.modifiers[modifier])

    # Delete the old mesh and rename the data block
    bpy.data.meshes.remove(old_mesh)
    obj.data.name = old_mesh_name

    # restore the previously enabled modifiers
    if len(saved_enabled_modifiers) > 0:
        for modifier in saved_enabled_modifiers:
            modifier.show_viewport = True


def save_shape_key_properties(obj):
    ''' This function will save the settings on the shape keys (min/max etc) and return them as a dictionary'''
    properties_dict = {}
    for idx, key_block in enumerate(obj.data.shape_keys.key_blocks): # will skip index 0 (Basis)
        if idx == 0:
            continue
        properties_object = {p.identifier: getattr(key_block, p.identifier) for p in key_block.bl_rna.properties if not p.is_readonly}
        properties_dict[key_block.name] = {"properties": properties_object}
    return properties_dict


def restore_shape_key_properties(obj, property_dict):
    ''' Restores the settings for each shape key (min/max etc) '''
    for idx, key_block in enumerate(obj.data.shape_keys.key_blocks): # will skip index 0 (Basis)
        if idx == 0:
            continue
        properties = list(property_dict.items())[idx - 1][1]['properties']
        for prop, value in properties.items():
                setattr(key_block, prop, value)

def join_as_shape(temp_obj, original_obj):
    '''Join the temp object back to the original as a shape key 
    Vertex positions are transferred by index.
    Different number of vertices or index will give unpredictable results
    '''

    # create a basis shape on the temp object to make the next step easier
    temp_obj_shape = temp_obj.shape_key_add(from_mix=False)
    # temp_obj_verts = temp_obj.data.shape_keys.key_blocks[1:]
    new_org_shape = original_obj.shape_key_add(from_mix=False)

    # Transfer Vertex Positions
    for source_vert, target_vert in zip(temp_obj_shape.data, new_org_shape.data):
        target_vert.co = source_vert.co

    # return {'FINISHED'}


def save_shape_key_drivers(obj, property_dict):
    ''' Copy drivers for shape key properties by checking the property dictionary against the driver paths.
    returns a new dictionary with the drivers and the properties on the shape keys they drive'''

    drivers = {}

    # Ensure the object has shape keys animation data
    if not obj.data.shape_keys.animation_data:
        # print(f"No animation data found for {obj.name}.")  # DEBUG
        return drivers

    # Loop through all the drivers in the shape keys animation data
    for driver in obj.data.shape_keys.animation_data.drivers:
        # Only consider drivers related to shape key properties
        shape_key_drivers = []

        # Extract the property name from the data_path
        data_path_parts = driver.data_path.split('.')
        if len(data_path_parts) > 1:
            property_name = data_path_parts[-1]  # The last part of the data path is the property name (e.g. 'value', 'slider_min', 'slider_max')

            # Check if the property is in the dictionary
            properties = list(property_dict.items())

            # Find the shape key name using a regular expression
            match = re.search(r'key_blocks\["(.*)"\]', driver.data_path)

            shape_key_name = match.group(1)

            # Create a dictionary for the driver data
            driver_data = {
                "driver": driver,
                "property": property_name
            }

            # Append the driver data to the shape_key_drivers list
            if shape_key_name not in drivers:
                drivers[shape_key_name] = []

            drivers[shape_key_name].append(driver_data)

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
    if not target_obj.data.shape_keys.animation_data:
        target_obj.data.shape_keys.animation_data_create()  # Create animation data for the target shape key if needed
    target_obj.data.shape_keys.animation_data.action = source_obj.data.shape_keys.animation_data.action
    
    # Link the existing action slot to the action (Blender ver > 4.4)
    if bpy.app.version >= (4, 4, 0):
        target_obj.data.shape_keys.animation_data.action_slot = source_obj.data.shape_keys.animation_data.action_slot

    # print(f"Shape key animations copied from {source_obj.name} to {target_obj.name}.") # DEBUG


# Primary function (this gets imported and used by the operator)
def apply_modifiers_with_shape_keys(context, selected_modifiers):
    ''' Apply the selected modifiers to the mesh even if it has shape keys '''
    original_obj = context.view_layer.objects.active
    shapes_count = len(original_obj.data.shape_keys.key_blocks) if original_obj.data.shape_keys else 0
    error_message = None

    if shapes_count == 1: # if there is only a Basis shape, delete the shape and apply the modifiers
        original_obj.shape_key_remove(original_obj.data.shape_keys.key_blocks[0])
        apply_modifier_to_object(context, original_obj, selected_modifiers)
        return True, None

    # Save the pin option setting and active shape key index
    pin_setting = original_obj.show_only_shape_key
    saved_active_shape_key_index = original_obj.active_shape_key_index

    # Duplicate the object
    copy_obj = duplicate_object(original_obj)

    # Save the shape key properties
    shape_key_properties = save_shape_key_properties(original_obj)

    # Copy drivers for shape keys (from the copy because the original ones will be gone in a moment)
    shape_key_drivers = save_shape_key_drivers(copy_obj, shape_key_properties[original_obj.active_shape_key.name])

    # Remove all shape keys and apply modifiers on the original
    bpy.ops.object.shape_key_remove(all=True)
    apply_modifier_to_object(context, original_obj, selected_modifiers)

    # Add a basis shape key back to the original object
    original_obj.shape_key_add(name=copy_obj.data.shape_keys.key_blocks[0].name,from_mix=False)

    # Loop over the original shape keys, create a temp mesh, apply single shape, apply modifers and merge back to the original (1 shape at a time)
    for i, (key_block_name, properties) in enumerate(shape_key_properties.items()):
        # Create a temp object
        context.view_layer.objects.active = copy_obj
        temp_obj = duplicate_object(copy_obj)

        # Pin the shape we want
        temp_obj.show_only_shape_key = True
        temp_obj.active_shape_key_index = i + 1 
        shape_key_name = temp_obj.active_shape_key.name
        temp_obj_old_mesh = temp_obj.data

        # Disable all modifiers (including selected)
        for modifier in temp_obj.modifiers:
            modifier.show_viewport = False
        
        # Now freeze the mesh by applying the selected modifiers
        apply_modifier_to_object(context, temp_obj, selected_modifiers)
        
        # Verify the meshes have the same amount of verts
        if len(original_obj.data.vertices) != len(temp_obj.data.vertices):
            error_message = f"{shape_key_name} failed because the mesh no longer have the same amount of vertices after applying selected modifier(s)."
            # Clean up the temp object and try to move on
            bpy.data.objects.remove(temp_obj)
            continue

        # Transfer the temp object as a shape back to orginal
        join_as_shape(temp_obj, original_obj)

        # Clean up the temp object
        bpy.data.meshes.remove(temp_obj.data)

    # Restore shape key properties
    restore_shape_key_properties(original_obj, shape_key_properties)

    # Restore any shape key animation
    copy_shape_key_animation(copy_obj, original_obj)

    # Restore any shape key drivers
    restore_shape_key_drivers(original_obj, copy_obj, shape_key_drivers, context)

    # Clean up the duplicate object
    bpy.data.meshes.remove(copy_obj.data)

    # Restore the pin option setting and active shape key index
    original_obj.show_only_shape_key = pin_setting
    original_obj.active_shape_key_index =  saved_active_shape_key_index

    # Make sure the original object is active before finishing
    context.view_layer.objects.active = original_obj

    # Report the error message if any
    if error_message:
        return False, error_message

    return True, None