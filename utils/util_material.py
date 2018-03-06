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
	# if the material is not in obj.materials, append it
	if not mat: return
	if mat.name not in obj.data.materials:
		link_mat(obj, mat)
	mat_index = list(obj.data.materials).index(mat)
	for face in faces:
		face.material_index = mat_index

def has_material(obj, name):
	return name in obj.data.materials.keys()

def template_create_materials(obj, name, defaults):
	mat_name = name
	if has_material(obj, mat_name):
		mat = obj.data.materials[mat_name]
	else:
		mat = create_mat(mat_name)
		link_mat(obj, mat)

		# set some material defaults
		diffuse 	= defaults.get('diffuse')
		diff_int 	= defaults.get('diffuse_intensity')
		specular 	= defaults.get('specular')
		spec_int 	= defaults.get('specular_intensity')
		set_defaults(mat, diffuse, diff_int, specular, spec_int)
	return mat


# FLOOR MATERIALS

def floor_mat_slab(obj):
	return template_create_materials(obj,
			"material_slab",
			{
				'diffuse' 			: (.4, .35, .3),
				'diffuse_intensity' : .8,
				'specular'			: (1, 1, 1),
				'specular_intensity': 0
			})

def floor_mat_wall(obj):
	return template_create_materials(obj,
			"material_wall",
			{
				'diffuse' 			: (.3, .25, .13),
				'diffuse_intensity' : .8,
				'specular'			: (1, 1, 1),
				'specular_intensity': 0
			})

# WINDOW MATERIALS

def window_mat_frame(obj):
	return template_create_materials(obj,
			"material_frame",
			{
				'diffuse' 			: (.8, .8, .8),
				'diffuse_intensity' : 1,
				'specular'			: (1, 1, 1),
				'specular_intensity': 0
			})

def window_mat_pane(obj):
	return template_create_materials(obj,
			"material_pane",
			{
				'diffuse' 			: (0, .6, 0),
				'diffuse_intensity' : 1,
				'specular'			: (1, 1, 1),
				'specular_intensity': 0
			})

def window_mat_bars(obj):
	return template_create_materials(obj,
			"material_bar",
			{
				'diffuse' 			: (0, .6, .0),
				'diffuse_intensity' : 1,
				'specular'			: (1, 1, 1),
				'specular_intensity': 0
			})

def window_mat_glass(obj):
	return template_create_materials(obj,
			"material_glass",
			{
				'diffuse' 			: (0, .1, .6),
				'diffuse_intensity' : 1,
				'specular'			: (1, 1, 1),
				'specular_intensity': 0
			})
