import bpy

def create_mat(name="Default Material"):
	return bpy.data.materials.new(name)

def link_mat(obj, mat):
	obj.data.materials.append(mat)

def set_defaults(mat, diffuse, diff_int, specular, spec_int):
	mat.diffuse_color = diffuse
	mat.diffuse_intensity = diff_int
	mat.specular_color = specular
	mat.specular_intensity = spec_int

def material_set_faces(obj, mat, faces):
	mat_index = list(obj.data.materials).index(mat)
	for face in faces:
		face.material_index = mat_index

def has_material(obj, name):
	return name in obj.data.materials.keys()


# FLOOR MATERIALS

def floor_mat_slab(obj):
	mat_name = "material_slab"
	if has_material(obj, mat_name):
		mat = obj.data.materials[mat_name]
	else:
		mat = create_mat(mat_name)
		link_mat(obj, mat)

		# set some material defaults
		set_defaults(mat, (.4, .35, .3), .8, (1, 1, 1), 0)
	return mat

def floor_mat_wall(obj):
	mat_name = "material_wall"
	if has_material(obj, mat_name):
		mat = obj.data.materials[mat_name]
	else:
		mat = create_mat(mat_name)
		link_mat(obj, mat)

		# set some material defaults
		set_defaults(mat, (.3, .25, .13), .8, (1, 1, 1), 0)
	return mat
