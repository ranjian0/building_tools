
# Building Tools 2.0 — pip package for AI agents

> Procedural building generation on Blender's Python API — installable
> with pip, driven by rule files, headless renders and production exports.

## Quickstart (pip / agents)

```bash
pip install building-tools[bpy]
```

Write a rule file (`house.py`):

```python
def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=2, floor_height=3.0, wall_thickness=0.25)
    ctx.interior(partition_mode="TREEMAP", room_count=4, inset=0.25)
    ctx.windows(storeys=(1,), fill_type="GLASS_PANES")
    ctx.roof(type="GABLE", height=1.8, add_gutters=True)
    ctx.render("confirm.png", views=("front", "iso"))
    ctx.export("house.glb")
```

Then:

```bash
btools run house.py --json
```

Same seed, same building. `--render` writes confirmation PNGs, `--export`
writes production assets with semantic material slots (`BT_walls`,
`BT_roof`, ...). Exit code is 0 iff every step succeeded — pipe the JSON
summary straight into your agent loop.

CLI reference: `btools --help`, `btools run --help`,
`btools list-presets --json`, `btools smoke`.

---

# Building Tools 1.x — Blender addon (legacy)

> ⚡️ Crazy fast way to model buildings in Blender!

Artists should redirect to: https://ranjian0.github.io/building_tools/

The 1.x addon UI is frozen at release v1.0.13 — install that release
from the GitHub releases page if you want the Blender-side panel.
Development continues on the pip package above.


## Table of contents

* [Background](#background)
* [Usage](#usage)
* [Installation](#installation)
* [Features](#features)
* [Status](#status)
* [Inspiration](#inspiration)
* [Contributing](#contributing)
* [Authors](#authors)

## Background

This addon started out as a collection of scripts used to create 3d models for games.

After a couple of months of development, I noticed that most of the scripts were geared
towards creating buildings and environments. I decided to create a proper addon for them
and `Building Tools` was born.

## Usage

[![Tutorial Videos](http://img.youtube.com/vi/rB1fm4I_bW4/0.jpg)](http://www.youtube.com/watch?v=rB1fm4I_bW4)

## Installation

1. Download add-on (zipped) from this [link](https://github.com/ranjian0/building_tools/releases/download/v1.0.13/building_tools_v1.0.13.zip).
2. In blender, go to : Edit -> Preferences -> Add-ons -> Install.
3. Select the downloaded file and you're good to go.


## Features

* [Floorplans](https://github.com/ranjian0/building_tools/wiki/Floorplan)
* [Floors](https://github.com/ranjian0/building_tools/wiki/Floor)
* [Doors](https://github.com/ranjian0/building_tools/wiki/Door)
* [Windows](https://github.com/ranjian0/building_tools/wiki/Window)
* [Multigroup](https://github.com/ranjian0/building_tools/wiki/Multigroup) (door-window combinations)
* [Roof](https://github.com/ranjian0/building_tools/wiki/Roof)
* [Stairs](https://github.com/ranjian0/building_tools/wiki/Stairs)
* [Balcony](https://github.com/ranjian0/building_tools/wiki/Balcony)
* **Building Presets** — one-click complete buildings (suburban house,
  townhouse, apartment block, modern villa, mediterranean villa, corner
  shop, warehouse, office block) with floor-count and footprint scaling

## Status

`Version` : `v1.0.13`

**Blender 4.0 Compatible** 

## Inspiration

Project inspired by `Ghost Town` addon for `3DS MAX`.

## Contributing

  * Feel free to fork and submit pull requests.

  * Incase of bugs, create an issue that describes the problem
    and attach any relevant info/logs.

  * For feature requests, create an issue and add **Enhancement** label.

  You can chat with other contributors over at our [discord server](https://discord.gg/hK4UaGu).

## Authors

Created by [ranjian0](https://github.com/ranjian0), [luckykadam](https://github.com/luckykadam) and [MCrafterzz](https://github.com/MCrafterzz). Feel free to contact.

## Support

If you would like to support our work you can do so through Paypal,

[![](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate?hosted_button_id=EX6AB8P8M9VZG)
