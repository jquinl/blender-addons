bl_info = {
    "name": "Distribute in Grid",
    "blender": (4, 0, 0),
    "category": "Object",
}

import copy
import bpy
from bpy.props import FloatProperty, IntProperty, EnumProperty, BoolProperty, StringProperty
import numpy as np
from mathutils import Vector

class DistributeObjectsGrid(bpy.types.Operator):
    """Object Cursor Array"""
    bl_idname = "object.distribute_grid"
    bl_label = "Distribute objects"
    bl_options = {'REGISTER', 'UNDO'}

    total: bpy.props.IntProperty(name="Steps", default=2, min=1, max=100)
    
    mode : EnumProperty(
        name='Mode',
        description="Distribution options",
        items=[
            ("MIN", "Compact", "Minimum space without overlap"),
            ("EQUIV", "Even space", "Even space without overlap"),
            ("DISTANCE", "Distance", "User defined distance"),
            ],
        default="MIN"
    )
    plane : EnumProperty(
        name='Plane',
        description="Plane of grid",
        items=[
            ("XY_PLANE", "XY Plane", ""),
            ("YX_PLANE", "YX Plane", ""),
            ("XZ_PLANE", "XZ Plane", ""),
            ("ZX_PLANE", "ZX Plane", ""),
            ("YZ_PLANE", "YZ Plane", ""),
            ("ZY_PLANE", "ZY Plane", ""),
            ],
        default="XY_PLANE"
    )
    distance1 : FloatProperty(
        name='Distance 1',
        description="Distance between objects in fist dimension",
        min=0.0,
        default=1.0,
    )
    distance2 : FloatProperty(
        name='Distance 2',
        description="Distance between objects in second dimension",
        min=0.0,
        default=1.0,
    )
    padding : FloatProperty(
        name='Padding',
        description="Separation between objects",
        min=0.0,
        default=0.1,
    )
    rows : IntProperty(
        name = 'Rows',
        description = "Rows of the grid",
        min = 1,
        default = 1
    )
    size_sort : EnumProperty(
        name = 'Sort by size',
        description = "Sort objects by size",
        items=[
            ("SMALLEST", "Smallest first", ""),
            ("BIGGEST", "Biggest first", ""),
            ("WHATEVER", "Whatever", ""),
            ],
        default = "SMALLEST"
    )
    def draw(self,context):
        layout = self.layout
        row = layout.row(align=True)
        row.prop(self, 'mode')
        if(self.mode == "MIN"):
            row = layout.row(align=True)
            row.prop(self, 'plane')
        if(self.mode == "EQUIV"):
            row = layout.row(align=True)
            row.prop(self, 'plane')
        elif self.mode == "DISTANCE":
            row = layout.row(align=True)
            row.prop(self, 'plane')
            row = layout.row(align=True)
            row.prop(self, 'distance1')
            row.prop(self, 'distance2')
        row = layout.row(align=True)
        row.prop(self, 'rows')
        row = layout.row(align=True)
        row.prop(self, 'size_sort')
        row = layout.row(align=True)
        row.prop(self, 'padding')
    
    def execute(self, context):
        scene = context.scene
        cursor = scene.cursor.location
        obj = context.active_object
        objs =  context.selected_objects
        obj_num = len(objs)

        self.rows = min(self.rows,obj_num)
        if obj_num < 2:
            return {'FINISHED'}
        corner = copy.deepcopy(cursor)
        
        #get object bounding box
        distances = np.array([self.aabb_distance(o) for o in objs])
        #get their areas and sort if selected 
        X,Y,Z = (0,1,2)

        d1,d2,d3 = (X,Y,Z)
        if self.plane == "XZ_PLANE":
            d1,d2,d3 = (X,Z,Y)
        elif self.plane == "YZ_PLANE":
            d1,d2,d3 = (Y,Z,X)
        elif self.plane == "YX_PLANE":
            d1,d2,d3 = (Y,X,Z)
        elif self.plane == "ZY_PLANE":
            d1,d2,d3 = (Z,Y,X)
        elif self.plane == "ZX_PLANE":
            d1,d2,d3 = (Z,X,Y)

        areas = np.multiply(distances[:,d1],distances[:,d2])

        sorting = np.array(range(len(objs)))
        if self.size_sort == "SMALLEST":
            sorting = np.argsort(areas)
        if self.size_sort == "BIGGEST":
            sorting = np.flip(np.argsort(areas))

        #get how many columns are needed for the objects
        extra = obj_num % self.rows
        cols = obj_num // self.rows

        if cols == 0:
            self.report({'WARNING'},"Too many rows")
            return {'FINISHED'}
        
        if extra != 0:
            cols += 1
        
        if cols * (self.rows - 1)>= obj_num : 
            self.report({'WARNING'},"Number of rows chosen generates empty rows")
            return {'FINISHED'}
    
                
        padding1 = np.array([self.padding * (i % cols) for i in range(obj_num)])
        padding2 = np.array([self.padding * i for i in range(self.rows)])

        if(self.mode == "MIN"):
            padding1 = np.array([self.padding * (i % cols) for i in range(obj_num)])

            hafldist1 = distances[sorting][:,d1] * 0.5
            centerdist =np.zeros(obj_num)
            for i in range(1,obj_num):
                if i % cols == 0:
                    continue
                centerdist[i] = hafldist1[i] + hafldist1[i-1] + centerdist[i-1]
            d1pads  = centerdist + padding1

            hafldist2 = np.zeros(self.rows)
            for i in range(self.rows):
                hafldist2[i] = np.max(distances[sorting][i * cols :min(obj_num,(i+1)* cols),d2]) * 0.5
            
            d2pads = np.zeros(self.rows)
            for i in range(1,self.rows):
                d2pads[i] = hafldist2[i] + hafldist2[i-1] + d2pads[i-1]

            d2pads += padding2

            for ip,iob in enumerate(sorting):
                objs[iob].location[d1] = d1pads[ip] + corner[d1]
                objs[iob].location[d2] = d2pads[ip//cols] + corner[d2]
                objs[iob].location[d3] = corner[d3]
            return {'FINISHED'}

        dist1 = self.distance1
        dist2 = self.distance1

        if(self.mode == "EQUIV"):
            dist1 = np.max(distances[:,d1])
            dist2 = np.max(distances[:,d2])

        for ip,iob in enumerate(sorting):
            i_pos = ip % cols
            j_pos = ip // cols
            objs[iob].location[d1] = i_pos * dist1 + corner[d1] + padding1[i_pos]
            objs[iob].location[d2] = j_pos * dist2 + corner[d2] + padding2[j_pos]
            objs[iob].location[d3] = corner[d3]
            
        return {'FINISHED'}

    def aabb_distance(self,obj):
        bbox_corners = np.array([obj.matrix_world @ Vector(corner) for corner in obj.bound_box])
        return np.array([
            np.max(bbox_corners[:,0]) - np.min(bbox_corners[:,0]),
            np.max(bbox_corners[:,1]) - np.min(bbox_corners[:,1]),
            np.max(bbox_corners[:,2]) - np.min(bbox_corners[:,2]),
        ])


def menu_func(self, context):
    self.layout.operator(DistributeObjectsGrid.bl_idname)

def register():
    bpy.utils.register_class(DistributeObjectsGrid)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(DistributeObjectsGrid)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()