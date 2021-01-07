import bpy
import btools
import random


class BuildingGenerator:
    _props = None

    @staticmethod
    def build_random():
        floorplan = FloorplanGenerator().build_random()

        # Switch Context
        old_mode = bpy.context.mode
        if  old_mode != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")

        FloorGenerator(floorplan=floorplan).build_random()

        # Reset Context
        bpy.ops.object.mode_set(mode=old_mode)
        return floorplan


class FloorplanGenerator:
    _props = None
    _builder = btools.building.floorplan.floorplan.Floorplan
    _prop_class = btools.building.floorplan.FloorplanProperty

    def __init__(self):
        self.context = bpy.context 
        self.scene = bpy.context.scene
        self._register()

    def __del__(self):
        self._unregister()

    @staticmethod
    def _unregister():
        del bpy.types.Scene.prop_floorplan

    def _register(self):
        """ Register Property
        """
        try:
            bpy.utils.register_class(self._prop_class)
        except ValueError:
            pass # XXX Already registered
        bpy.types.Scene.prop_floorplan = bpy.props.PointerProperty(type=self._prop_class)
        self._props = btools.utils.dict_from_prop(self.scene.prop_floorplan)

    def build_from_props(self, pdict):
        """ Build floorplan from given pdict args
        see floorplan.FloorplanProperty 
        
        `pdict` should be a dict with any of the following keys:
        {
            "type" -> {"RECTANGULAR", "H-SHAPED, "RANDOM", "COMPOSITE", "CIRCULAR"},
            "width", "tw1", "tw2", "tw3", "tw4" -> float,
            "length", "tl1", "tl2", "tl3", "tl4" -> float,

            "seed" -> int[0, 10000],
            "extension_amount" -> int[1, 4],
            "random_extension_amount" -> bool,

            "radius" -> float,
            "segments" -> int[3, 100],
        }
        """
        self._props.update(pdict)
        btools.utils.prop_from_dict(self.scene.prop_floorplan, pdict)
        return self._builder.build(self.context, self.scene.prop_floorplan)

    def build_random(self):
        properties = btools.utils.dict_from_prop(self._prop_class)
        properties['type'] = random.choices(
            ["RECTANGULAR", "H-SHAPED", "RANDOM", "COMPOSITE"] # Circular not very usefull, "CIRCULAR"],
            weights=[0.8, 0.5, 0.8, 0.7], k=1
        )[-1]

        # Main Sizing
        if properties['type'] in ["RECTANGULAR", "H-SHAPED", "RANDOM", "COMPOSITE"]:
            properties['width'] = random.choice(range(2, 5))
            properties['length'] = random.choice(range(2, 5))
        else:
            properties['radius'] = random.choice(range(2, 5))

        # Random floorplan options
        if properties['type'] == "RANDOM":
            properties['seed'] = random.randint(0, 1000)
            properties['extension_amount'] = random.randint(1, 3)

        # Composite floorplan options
        if properties['type'] == "COMPOSITE":
            for ke in ["tl1", "tl2", "tl3", "tl4"]:
                properties[ke] = random.choice(range(0, 5))

        # H-shaped floorplan options
        if properties['type'] == "H-SHAPED":
            for ke in ["tl1", "tl2", "tl3", "tl4"]:
                properties[ke] = random.choice(range(0, 5))

            for ke in ["tw1", "tw2", "tw3", "tw4"]:
                properties[ke] = btools.utils.clamp(
                    random.random() * max([properties['width'], properties['length']]) / 2,
                    1.0, 1000
                )
                
        return self.build_from_props(properties)


class FloorGenerator:
    _props = None
    _builder = btools.building.floor.floor.Floor
    _prop_class = btools.building.floor.FloorProperty

    def __init__(self,floorplan=None):
        self.context = bpy.context 
        self.scene = bpy.context.scene
        self._register()
        
        if floorplan and isinstance(floorplan, bpy.types.Object):
            bpy.context.view_layer.objects.active = floorplan

        if self.context.mode != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")

    def __del__(self):
        self._unregister()

    @staticmethod
    def _unregister():
        del bpy.types.Scene.prop_floor

    def _register(self):
        """ Register Property
        """
        try:
            bpy.utils.register_class(self._prop_class)
        except ValueError:
            pass # XXX Already registered
        bpy.types.Scene.prop_floor = bpy.props.PointerProperty(type=self._prop_class)
        self._props = btools.utils.dict_from_prop(self.scene.prop_floor)

    def build_from_props(self, pdict):
        """ Build floors from given pdict args
        see floor.FloorProperty 
        
        `pdict` should be a dict with any of the following keys:
        {
            "floor_count" -> int[0, 10000],
            "floor_height" -> float,

            "slab_thickness" -> float,
            "slab_outset" -> float

            "add_slab" -> bool,
            "add_columns" -> bool,
        }
        """
        self._props.update(pdict)
        btools.utils.prop_from_dict(self.scene.prop_floor, pdict)
        return self._builder.build(self.context, self.scene.prop_floor)

    def build_random(self):
        properties = btools.utils.dict_from_prop(self._prop_class)

        properties['add_columns'] = False 
        properties['add_slabs'] = True

        properties['floor_count'] = random.choice(range(10))
        return self.build_from_props(properties)
