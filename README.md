
# CYNTHIA BUILDING GENERATOR

## Purpose:

> Provide a quick way to model buildings in blender


## Features:

1. Create Floorplan
	* Provide a set of basic floorplan shapes to build geometry from

2. Create Floors
	* Extrude floorplan shapes to create walls

3. Add Windows
	* Add window geometry to walls

4. Add Doors
	* Add door geometry to walls

## Development Status

    Inspite of my sincerest efforts to bring intuitive building generation
    tools to blender, I have consistently failed as a result of blender's
    rigid operator design and user interaction philosophy.

    In particular:-
     - Blender Operators are data oriented, this means you have to define all data
       that an operator will consume beforehand. Moreover, the data consumed by an operator
       must exist as one of the property types defined by blender's api.

       While this in itself is not particulary BAD, if your addon supports lots of
       options, it means you have to manually define lots of properties.

       Moreover, where this properties should be stored can occassionally be non-obvious.

       On the one hand, you can store the properties in the operator that needs them. This unfortunately
       means that the properties cannot be accessed when the operator is not running.

       Or, you can store the properties globally eg register them in the scene


