import bpy
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

# XXX Cache for holding PrincipledBSDFWrappers for all materials
MAT_WRAPPER_CACHE = {}

def create_mat(name="Default Material"):
	mat = bpy.data.materials.get(name, bpy.data.materials.new(name))
	mat_wrap = MAT_WRAPPER_CACHE.get(mat, None)
	if not mat_wrap:
		mat_wrap = PrincipledBSDFWrapper(mat, is_readonly=False)
		mat_wrap.use_nodes = True
		MAT_WRAPPER_CACHE[mat] = mat_wrap
	return mat

def link_mat(obj, mat):
	if not has_material(obj, mat.name):
		obj.data.materials.append(mat)

def create_material_group(obj, group_name):
	# create material
	mat = create_mat(group_name+"_mat")
	link_mat(obj, mat)

	# Create group in none exists
	if group_name not in [g.name for g in obj.mat_groups]:
		group = obj.mat_groups.add()
		group.name = group_name
		group.material = mat
		obj.mat_group_index = len(obj.mat_groups)-1

def get_material_wrapper(mat):
	return MAT_WRAPPER_CACHE.get(mat, PrincipledBSDFWrapper(mat, is_readonly=False))

def material_set_faces(obj, mat, faces):
	# if the material is not in obj.materials, append it
	if not mat: return
	if mat.name not in obj.data.materials:
		link_mat(obj, mat)
	mat_index = list(obj.data.materials).index(mat)
	for face in faces:
		face.material_index = mat_index

def has_material(obj, name):
	return name in obj.data.materials.keys()


DEFAULT_BASE_COLORS = {
	"mat_slab" : (.4, .35, .3),
	"mat_wall" : (.3, .25, .13),

	"mat_window_frame" : (.8, .8, .8),
	"mat_window_pane"  : (0, .6, 0),
	"mat_window_bars"  : (0, .7, 0),
	"mat_window_glass" : (0, .1, .6),

	"mat_door_frame" : (.8, .8, .8),
	"mat_door_pane"  : (.13, .05, 0),
	"mat_door_groove" : (.13, .05, 0),
	"mat_door_glass"  : (0, .1, .6)
}