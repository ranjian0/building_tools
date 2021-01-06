import bpy
import btools
import random

class FloorplanGenerator:
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

    def build_from_props(self, pdict):
        """ Build floorplan from given pdict (kwargs)
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
        btools.utils.prop_from_dict(self.scene.prop_floorplan, pdict)
        return self._builder.build(self.context, self.scene.prop_floorplan)

    def build_random(self):
        properties = btools.utils.dict_from_prop(self._prop_class)
        properties['type'] = random.choice([
            # "RECTANGULAR", "H-SHAPED", "RANDOM", "COMPOSITE", "CIRCULAR"
            "H-SHAPED"
        ])

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
