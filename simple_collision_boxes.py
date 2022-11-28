import bpy

bl_info = {
	"name": "Create simple collision mesh",
	"author": "Jon Eunan Quinlivan Domínguez",
	"version": (1, 0),
	"blender": (3, 3, 1),
	"location": "View3D > Add > Mesh > Create Collision Mesh",
	"description" : "Create simplified meshes for collision meshes using vertex bounding boxes",
	"warning": "",
    "doc_url": "",
	"category": "Add Mesh",
}

import bpy
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper
from bpy.props import FloatProperty, IntProperty, EnumProperty, BoolProperty, StringProperty

class OBJECT_OT_create_collision(Operator):
    bl_idname = "mesh.create_simple_collision"
    bl_label = "Create Simplified Collision Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    axis : EnumProperty(
        name='Axis',
        description="Subdivide along Axis",
        items=[
            ("X_AXIS", "X axis", ""),
            ("Y_AXIS", "Y axis", ""),
            ("Z_AXIS", "Z axis", ""),
            ],
        default="X_AXIS"
    )

    subdiv_type : EnumProperty(
        name='Mode',
        description="Mode of subdivision applied",
        items=[
            ("DIV", "By Subdivsion Number", ""),
            ("CHK", "By Box Size", ""),
            ],
        default="DIV"
    )

    collapse : EnumProperty(
        name='Collapse',
        description="Collapse all bounding boxes into a single one",
        items=[
            ("NON", "No collapse", ""),
            ("AVG", "Collapse to average", ""),
            ("MIN", "Collapse to minimum", ""),
            ],
        default="NON"
    )

    div : IntProperty(
        name='Subdivision Number',
        description="Number of bounding boxes generated",
        min=1, max=100000,
        default=1,
    )

    chk : FloatProperty(
        name='Box Size',
        description="Size of chunk in axis",
        min=0.001, max=100000.0,
        default=1,
    )

    offset : FloatProperty(
        name='Offset',
        description="Subdivision Offset",
        min=-100000.0, max=100000.0,
        default=0.0,
    )

    force_vol : BoolProperty(
        name='Force Fill Axis',
        description="Subdivisions include all vertices along the axis",
        default=True,
    )
    shared_mesh : BoolProperty(
        name='Shared mesh',
        description="All selected objects will generate the same mesh",
        default=False,
    )

    parent : BoolProperty(
        name='Auto child',
        description="Make generated object a child of the original mesh",
        default=True,
    )

    suffix: StringProperty(
        name='Name suffix',
        default="-colonly",
        maxlen=255,
    )

    def execute(self, context):

        self.genereate_bb_col(context)

        return {'FINISHED'}

    def draw(self,context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, 'axis')
        row = layout.row(align=True)
        row.prop(self, 'subdiv_type')
        row = layout.row(align=True)
        if(self.subdiv_type == "DIV"):
            row = layout.row(align=True)
            row.prop(self, 'div')
        if(self.subdiv_type == "CHK"):
            row = layout.row(align=True)
            row.prop(self, 'chk')

        row = layout.row(align=True)
        row.prop(self,'offset')
        row = layout.row(align=True)
        row.prop(self,'collapse')
        row = layout.row(align=True)
        row.prop(self,'force_vol')
        row = layout.row(align=True)
        row.prop(self,'shared_mesh')
        row = layout.row(align=True)
        row.prop(self,'parent')
        row = layout.row(align=True)
        row.prop(self,'suffix')

    def genereate_bb_col(self, context):

        selection = bpy.context.selected_objects

        edges=[]
        bb_verts = []
        faces = []
        for ct,m_object in enumerate(selection):


            bb_mesh = bpy.data.meshes.new(name=m_object.name + "_colmesh")

            if(not self.shared_mesh or ct == 0):
                if(self.subdiv_type == "DIV"):
                    bb_verts = self.divide_mesh_by_div(context,m_object.data.vertices)
                elif(self.subdiv_type == "CHK"):
                    bb_verts = self.divide_mesh_by_chk(context,m_object.data.vertices)

                if(self.collapse != "NON"):
                    bb_verts = self.collapse_bb(context,bb_verts)

                if(len(bb_verts)>7):
                    faces = self.make_faces(context,bb_verts)

            bb_mesh.from_pydata(bb_verts, edges, faces)
            bb_mesh.update()
           
            obj_name = m_object.name + self.suffix
            bb_object=bpy.data.objects.new(obj_name, bb_mesh)

            bpy.context.collection.objects.link(bb_object)

            if(self.parent):
                bb_object.parent=m_object

    def divide_mesh_by_div(self,context,vertices):

        minX = min([vert.co[0] for vert in vertices])
        maxX = max([vert.co[0] for vert in vertices])
        minY = min([vert.co[1] for vert in vertices])
        maxY = max([vert.co[1] for vert in vertices])
        minZ = min([vert.co[2] for vert in vertices])
        maxZ = max([vert.co[2] for vert in vertices])

        full_bb_verts = []

        if(self.div == 1):
            full_bb_verts.extend(self.bounding_box_verts(context,vertices))
        else:
            if(self.axis == "X_AXIS"):
                chunk = float((maxX-minX)/self.div)
                min_pos  = minX + self.offset
                for i in range(self.div):
                    verts = [v for v in vertices if (v.co[0] >= min_pos + (chunk * i))  and (v.co[0] < min_pos + (chunk * (i + 1)))]
                    if(self.force_vol and i == 0):
                        verts = [v for v in vertices if (v.co[0] < min_pos + (chunk))]
                    if(self.force_vol and i == self.div - 1):
                        verts = [v for v in vertices if (v.co[0] >= min_pos + (chunk * i))]
                    bb_v = self.bounding_box_verts(context,verts)

                    full_bb_verts.extend(bb_v)

            if(self.axis == "Y_AXIS"):
                chunk = float((maxY-minY)/self.div) 
                min_pos  = minY + self.offset
                for i in range(self.div):
                    verts = [v for v in vertices if (v.co[1] >= min_pos + (chunk * i))  and (v.co[1] < min_pos + (chunk * (i + 1)))]
                    if(self.force_vol and i == 0):
                        verts = [v for v in vertices if (v.co[1] < min_pos + (chunk))]
                    if(self.force_vol and i == self.div - 1):
                        verts = [v for v in vertices if (v.co[1] >= min_pos + (chunk * i))]
                    bb_v = self.bounding_box_verts(context,verts)

                    full_bb_verts.extend(bb_v)

            if(self.axis == "Z_AXIS"):
                chunk = float((maxZ-minZ)/self.div) 
                min_pos  = minZ + self.offset
                for i in range(self.div):
                    verts = [v for v in vertices if (v.co[2] >= min_pos + (chunk * i))  and (v.co[2] < min_pos + (chunk * (i + 1)))]
                    if(self.force_vol and i == 0):
                        verts = [v for v in vertices if (v.co[2] < min_pos + (chunk))]
                    if(self.force_vol and i == self.div - 1):
                        verts = [v for v in vertices if (v.co[2] >= min_pos + (chunk * i))]
                    bb_v = self.bounding_box_verts(context,verts)

                    full_bb_verts.extend(bb_v)

        return full_bb_verts 


    def divide_mesh_by_chk(self,context,vertices):

        minX = min([vert.co[0] for vert in vertices])
        maxX = max([vert.co[0] for vert in vertices])
        minY = min([vert.co[1] for vert in vertices])
        maxY = max([vert.co[1] for vert in vertices])
        minZ = min([vert.co[2] for vert in vertices])
        maxZ = max([vert.co[2] for vert in vertices])

        faces = []
        full_bb_verts = []

        if(self.axis == "X_AXIS"):
            div = int((maxX-minX)/self.chk)
            if(div == 0):
                self.report({'INFO'}, 'Chunks too big, will default to single bounding box')
                bb_v = self.bounding_box_verts(context,vertices)
                full_bb_verts.extend(bb_v)

            elif(div == 1):
                self.report({'INFO'}, 'Chunks too big, will default to single bounding box')
                min_pos  = minX +self.offset
                if(self.force_vol):
                    bb_v = self.bounding_box_verts(context,vertices)
                else:
                    verts = [v for v in vertices if v.co[0] >= min_pos   and (v.co[0] < min_pos + self.chk)]
                    bb_v = self.bounding_box_verts(context,verts)
                full_bb_verts.extend(bb_v)

            else:
                min_pos  = minX +self.offset
                for i in range(div):
                    verts = [v for v in vertices if (v.co[0] >= min_pos + (self.chk * i))  and (v.co[0] < min_pos + (self.chk * (i + 1)))]
                    if(self.force_vol and i == div - 1):
                        verts = [v for v in vertices if (v.co[0] >= min_pos + (self.chk * i))]
                    elif(self.force_vol and i == 0):
                        verts = [v for v in vertices if (v.co[0] >= minX ) and (v.co[0] < min_pos + self.chk)]
                    bb_v = self.bounding_box_verts(context,verts)
                    full_bb_verts.extend(bb_v)

        if(self.axis == "Y_AXIS"):
            div = int((maxY-minY)/self.chk)
            if(div == 0):
                self.report({'INFO'}, 'Chunks too big, will default to single bounding box')
                bb_v = self.bounding_box_verts(context,vertices)
                full_bb_verts.extend(bb_v)

            elif(div == 1):
                self.report({'INFO'}, 'Chunks too big, will default to single bounding box')
                min_pos  = minY +self.offset
                if(self.force_vol):
                    bb_v = self.bounding_box_verts(context,vertices)
                else:
                    verts = [v for v in vertices if v.co[1] >= min_pos   and (v.co[1] < min_pos + self.chk)]
                    bb_v = self.bounding_box_verts(context,verts)
                full_bb_verts.extend(bb_v)

            else:
                min_pos  = minY +self.offset
                for i in range(div):
                    verts = [v for v in vertices if (v.co[1] >= min_pos + (self.chk * i))  and (v.co[1] < min_pos + (self.chk * (i + 1)))]
                    if(self.force_vol and i == div - 1):
                        verts = [v for v in vertices if (v.co[1] >= min_pos + (self.chk * i))]
                    elif(self.force_vol and i == 0):
                        verts = [v for v in vertices if (v.co[1] >= minY ) and (v.co[1] < min_pos + self.chk)]
                    bb_v = self.bounding_box_verts(context,verts)
                    full_bb_verts.extend(bb_v)

        if(self.axis == "Z_AXIS"):
            div = int((maxZ-minZ)/self.chk)
            if(div == 0):
                self.report({'INFO'}, 'Chunks too big, will default to single bounding box')
                bb_v = self.bounding_box_verts(context,vertices)
                full_bb_verts.extend(bb_v)

            elif(div == 1):
                self.report({'INFO'}, 'Chunks too big, will default to single bounding box')
                min_pos  = minZ +self.offset
                if(self.force_vol):
                    bb_v = self.bounding_box_verts(context,vertices)
                    
                else:
                    verts = [v for v in vertices if v.co[2] >= min_pos   and (v.co[2] < min_pos + self.chk)]
                    bb_v = self.bounding_box_verts(context,verts)
                full_bb_verts.extend(bb_v)

            else:
                min_pos  = minZ +self.offset
                for i in range(div):
                    verts = [v for v in vertices if (v.co[2] >= min_pos + (self.chk * i))  and (v.co[2] < min_pos + (self.chk * (i + 1)))]
                    if(self.force_vol and i == div - 1):
                        verts = [v for v in vertices if (v.co[2] >= min_pos + (self.chk * i))]
                    elif(self.force_vol and i == 0):
                        verts = [v for v in vertices if (v.co[2] >= minZ ) and (v.co[2] < min_pos + self.chk)]
                    bb_v = self.bounding_box_verts(context,verts)
                    full_bb_verts.extend(bb_v)


        return full_bb_verts

    def collapse_bb(self,context,full_bb_verts):
        if(len(full_bb_verts)<8): return []

        if(self.collapse == "AVG"):
            def div_axis(verts,rest):
                x,y,z=[],[],[]
                for c,v in enumerate(full_bb_verts):
                    if c % 8 == rest:
                        x.append(v[0])
                        y.append(v[1])
                        z.append(v[2])
                return x,y,z
            verts0_x,verts0_y,verts0_z = div_axis(full_bb_verts,0)
            verts1_x,verts1_y,verts1_z = div_axis(full_bb_verts,1)
            verts2_x,verts2_y,verts2_z = div_axis(full_bb_verts,2)
            verts3_x,verts3_y,verts3_z = div_axis(full_bb_verts,3)
            verts4_x,verts4_y,verts4_z = div_axis(full_bb_verts,4)
            verts5_x,verts5_y,verts5_z = div_axis(full_bb_verts,5)
            verts6_x,verts6_y,verts6_z = div_axis(full_bb_verts,6)
            verts7_x,verts7_y,verts7_z = div_axis(full_bb_verts,7)

            v_0 = [sum(verts0_x)/len(verts0_x),sum(verts0_y)/len(verts0_y),sum(verts0_z)/len(verts0_z)]
            v_1 = [sum(verts1_x)/len(verts1_x),sum(verts1_y)/len(verts1_y),sum(verts1_z)/len(verts1_z)]
            v_2 = [sum(verts2_x)/len(verts2_x),sum(verts2_y)/len(verts2_y),sum(verts2_z)/len(verts2_z)]
            v_3 = [sum(verts3_x)/len(verts3_x),sum(verts3_y)/len(verts3_y),sum(verts3_z)/len(verts3_z)]
            v_4 = [sum(verts4_x)/len(verts4_x),sum(verts4_y)/len(verts4_y),sum(verts4_z)/len(verts4_z)]
            v_5 = [sum(verts5_x)/len(verts5_x),sum(verts5_y)/len(verts5_y),sum(verts5_z)/len(verts5_z)]
            v_6 = [sum(verts6_x)/len(verts6_x),sum(verts6_y)/len(verts6_y),sum(verts6_z)/len(verts6_z)]
            v_7 = [sum(verts7_x)/len(verts7_x),sum(verts7_y)/len(verts7_y),sum(verts7_z)/len(verts7_z)]
            
            if(self.axis == "X_AXIS"):
                if(self.force_vol):
                    x_max = max([x[0] for x in full_bb_verts])
                    x_min = min([x[0] for x in full_bb_verts])
                    v_0[0],v_1[0],v_2[0],v_3[0] = x_min,x_min,x_min,x_min
                    v_4[0],v_5[0],v_6[0],v_7[0] = x_max,x_max,x_max,x_max
            if(self.axis == "Y_AXIS"):
                if(self.force_vol):
                    y_max = max([x[1] for x in full_bb_verts])
                    y_min = min([x[1] for x in full_bb_verts])
                    v_0[1],v_1[1],v_2[1],v_3[1] = y_min,y_min,y_min,y_min
                    v_4[1],v_5[1],v_6[1],v_7[1] = y_max,y_max,y_max,y_max
            if(self.axis == "Z_AXIS"):
                if(self.force_vol):
                    z_max = max([x[2] for x in full_bb_verts])
                    z_min = min([x[2] for x in full_bb_verts])
                    v_0[2],v_1[2],v_2[2],v_3[2] = z_min,z_min,z_min,z_min
                    v_4[2],v_5[2],v_6[2],v_7[2] = z_max,z_max,z_max,z_max
            v_0, v_1,v_2,v_3,v_4,v_5,v_6,v_7 = tuple(v_0), tuple(v_1),tuple(v_2),tuple(v_3),tuple(v_4),tuple(v_5),tuple(v_6),tuple(v_7) 
            return [v_0,v_1,v_2,v_3,v_4,v_5,v_6,v_7]
        if(self.collapse == "MIN"):

            def get_min_vol(verts):
                import math
                min_vol = 100000.0
                saved = 0
                for i in range(int(len(verts)/8)):
                    vol= (
                        math.sqrt((verts[i+1][0]-verts[i][0])**2 +(verts[i+1][1]-verts[i][1])**2 + (verts[i+1][2]-verts[i][2])**2) * 
                        math.sqrt((verts[i+3][0]-verts[i][0])**2 +(verts[i+3][1]-verts[i][1])**2 + (verts[i+3][2]-verts[i][2])**2) * 
                        math.sqrt((verts[i+4][0]-verts[i][0])**2 +(verts[i+4][1]-verts[i][1])**2 + (verts[i+4][2]-verts[i][2])**2) 
                        )
                    if(vol<min_vol):
                        min_vol = vol
                        saved = i
                return saved

            m = get_min_vol(full_bb_verts)
            v_0 = list(full_bb_verts[m])
            v_1 = list(full_bb_verts[m+1])
            v_2 = list(full_bb_verts[m+2])
            v_3 = list(full_bb_verts[m+3])
            v_4 = list(full_bb_verts[m+4])
            v_5 = list(full_bb_verts[m+5])
            v_6 = list(full_bb_verts[m+6])
            v_7 = list(full_bb_verts[m+7])

            if(self.axis == "X_AXIS"):
                if(self.force_vol):
                    x_max = max([x[0] for x in full_bb_verts])
                    x_min = min([x[0] for x in full_bb_verts])
                    v_0[0],v_1[0],v_2[0],v_3[0] = x_min,x_min,x_min,x_min
                    v_4[0],v_5[0],v_6[0],v_7[0] = x_max,x_max,x_max,x_max
            if(self.axis == "Y_AXIS"):
                if(self.force_vol):
                    y_max = max([x[1] for x in full_bb_verts])
                    y_min = min([x[1] for x in full_bb_verts])
                    v_0[1],v_1[1],v_2[1],v_3[1] = y_min,y_min,y_min,y_min
                    v_4[1],v_5[1],v_6[1],v_7[1] = y_max,y_max,y_max,y_max
            if(self.axis == "Z_AXIS"):
                if(self.force_vol):
                    z_max = max([x[2] for x in full_bb_verts])
                    z_min = min([x[2] for x in full_bb_verts])
                    v_0[2],v_1[2],v_2[2],v_3[2] = z_min,z_min,z_min,z_min
                    v_4[2],v_5[2],v_6[2],v_7[2] = z_max,z_max,z_max,z_max
            v_0, v_1,v_2,v_3,v_4,v_5,v_6,v_7 = tuple(v_0), tuple(v_1),tuple(v_2),tuple(v_3),tuple(v_4),tuple(v_5),tuple(v_6),tuple(v_7) 
            return [v_0,v_1,v_2,v_3,v_4,v_5,v_6,v_7]

        return []

    def make_faces(self,constext,verts):
        faces = []
        length = int(len(verts) / 8)
        for i in range(2*length -1):
            faces.extend([(0+4*i,4+4*i,7+4*i,3+4*i),(3+4*i,7+4*i,6+4*i,2+4*i),
                        (2+4*i,6+4*i,5+4*i,1+4*i),(1+4*i,5+4*i,4+4*i,0+4*i)])
        top = len(verts) -1
        faces.extend([(0,3,2,1),(top-3,top-2,top-1,top)])

        return faces
    def bounding_box_verts(self,context,vertices):
        if(len(vertices)< 2):
            self.report({'INFO'}, 'Too many subdivisions or offset too big, empty bounding boxes are being generated')
            return []
        minX = min([vert.co[0] for vert in vertices])
        maxX = max([vert.co[0] for vert in vertices])
        minY = min([vert.co[1] for vert in vertices])
        maxY = max([vert.co[1] for vert in vertices])
        minZ = min([vert.co[2] for vert in vertices])
        maxZ = max([vert.co[2] for vert in vertices])

        bb_verts = []
        if(self.axis == "X_AXIS"):
            bb_verts = [
                (minX,minY,minZ),
                (minX,maxY,minZ),
                (minX,maxY,maxZ),
                (minX,minY,maxZ), ## Xdirection 
                (maxX,minY,minZ),
                (maxX,maxY,minZ),
                (maxX,maxY,maxZ),
                (maxX,minY,maxZ),
                ]
        if(self.axis== "Y_AXIS"):
            bb_verts = [
                (minX,minY,minZ),
                (minX,minY,maxZ),
                (maxX,minY,maxZ),
                (maxX,minY,minZ),## Ydirection
                (minX,maxY,minZ),
                (minX,maxY,maxZ),
                (maxX,maxY,maxZ),
                (maxX,maxY,minZ),
                ]
        if(self.axis == "Z_AXIS"):
            bb_verts = [
                (minX,minY,minZ),
                (maxX,minY,minZ),
                (maxX,maxY,minZ),
                (minX,maxY,minZ),## Zdirection
                (minX,minY,maxZ),
                (maxX,minY,maxZ),
                (maxX,maxY,maxZ),
                (minX,maxY,maxZ),
                ]
        return bb_verts

def add_object_button(self, context):
		self.layout.operator(
            OBJECT_OT_create_collision.bl_idname,
            text= "Create Collision Mesh",
            icon="CLIPUV_HLT")

def register():
    bpy.utils.register_class(OBJECT_OT_create_collision)
    bpy.types.VIEW3D_MT_mesh_add.append(add_object_button)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_create_collision)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_object_button)

if __name__ == '__main__':
	register()

