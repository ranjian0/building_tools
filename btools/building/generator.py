import bpy
import btools

class FloorplanGenerator:
    _builder = btools.building.floorplan.floorplan.Floorplan
    _prop_class = btools.building.floorplan.FloorplanProperty

    def __init__(self):
        self.register()
        self.context = bpy.context 
        self.scene = bpy.context.scene

    def __del__(self):
        self.unregister()

    def register(self):
        """ Register Property
        """
        try:
            bpy.utils.register_class(self._prop_class)
        except ValueError:
            pass # XXX Already registered
        bpy.types.Scene.prop_floorplan = bpy.props.PointerProperty(type=self._prop_class)

    def unregister(self):
        del bpy.types.Scene.prop_floorplan

    def generate(self, pdict):
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
        self._builder.build(self.context, self.scene.prop_floorplan)
