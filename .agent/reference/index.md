# Reference corpus

image size: 1280x800 -- 42 cases

## scenario-wall

- status: `ok`
- faces: 6 -- geometry_hash: `696a9cb143dee764`

![scenario-wall](scenario-wall/image.png)

## scenario-curved-wall

- status: `ok`
- faces: 50 -- geometry_hash: `ae77a2dcde0752f2`

![scenario-curved-wall](scenario-curved-wall/image.png)

## scenario-floorplan

- status: `ok`
- faces: 1 -- geometry_hash: `274dfbcafe0bcb4b`

![scenario-floorplan](scenario-floorplan/image.png)

## scenario-floors-only

- status: `ok`
- faces: 49 -- geometry_hash: `6a35d08351c2e850`

![scenario-floors-only](scenario-floors-only/image.png)

## scenario-multi-storey

- status: `ok`
- faces: 60 -- geometry_hash: `251ca31659a2aaed`

![scenario-multi-storey](scenario-multi-storey/image.png)

## floorplan-circular

- status: `ok`
- faces: 1 -- geometry_hash: `5a24bad0e065fe38`

![floorplan-circular](floorplan-circular/image.png)

## floorplan-composite

- status: `ok`
- faces: 5 -- geometry_hash: `36e1aded8a4a87a1`

![floorplan-composite](floorplan-composite/image.png)

## floorplan-h-shaped

- status: `ok`
- faces: 7 -- geometry_hash: `8d8321ddda67589c`

![floorplan-h-shaped](floorplan-h-shaped/image.png)

## floorplan-random

- status: `ok`
- faces: 2 -- geometry_hash: `fb09b2c9a688e09c`

![floorplan-random](floorplan-random/image.png)

## floor-count-1

- status: `ok`
- faces: 17 -- geometry_hash: `3042ebd13bf34b78`

![floor-count-1](floor-count-1/image.png)

## floor-slabs-off

- status: `ok`
- faces: 13 -- geometry_hash: `10062cb82da91443`

![floor-slabs-off](floor-slabs-off/image.png)

## floor-columns

- status: `ok`
- faces: 73 -- geometry_hash: `b0b208f1cdb562bc`

![floor-columns](floor-columns/image.png)

## floor-decoration

- status: `ok`
- faces: 33 -- geometry_hash: `1ee79335baa8ab55`

![floor-decoration](floor-decoration/image.png)

## roof-flat

- status: `ok`
- faces: 65 -- geometry_hash: `b35807cb98e40918`

![roof-flat](roof-flat/image.png)

## roof-gable-open

- status: `ok`
- faces: 68 -- geometry_hash: `23907af2cc4b35c5`

![roof-gable-open](roof-gable-open/image.png)

## roof-gable-box

- status: `ok`
- faces: 62 -- geometry_hash: `c19fe454c2c5d6f7`

![roof-gable-box](roof-gable-box/image.png)

## roof-hip

- status: `ok`
- faces: 60 -- geometry_hash: `50c518289104647a`

![roof-hip](roof-hip/image.png)

## door-default

- status: `ok`
- faces: 22 -- geometry_hash: `39a2885c671af685`

![door-default](door-default/image.png)

## door-panels

- status: `ok`
- faces: 45 -- geometry_hash: `78745179f68c42bf`

![door-panels](door-panels/image.png)

## door-louver

- status: `ok`
- faces: 76 -- geometry_hash: `48d4e938b6b54642`

![door-louver](door-louver/image.png)

## door-glass-panes

- status: `ok`
- faces: 45 -- geometry_hash: `09afab203c22f74b`

![door-glass-panes](door-glass-panes/image.png)

## door-double

- status: `ok`
- faces: 23 -- geometry_hash: `0716bab0318c941e`

![door-double](door-double/image.png)

## door-arch

- status: `ok`
- faces: 44 -- geometry_hash: `eb12595929a7883c`

![door-arch](door-arch/image.png)

## window-default

- status: `ok`
- faces: 22 -- geometry_hash: `def25cfdadb6ea5f`

![window-default](window-default/image.png)

## window-bar

- status: `ok`
- faces: 28 -- geometry_hash: `265f4639c8e0b326`

![window-bar](window-bar/image.png)

## window-louver

- status: `ok`
- faces: 76 -- geometry_hash: `1d2c4e5b353064c3`

![window-louver](window-louver/image.png)

## window-glass-panes

- status: `ok`
- faces: 45 -- geometry_hash: `08f987660be83016`

![window-glass-panes](window-glass-panes/image.png)

## window-circular

- status: `ok`
- faces: 60 -- geometry_hash: `d2f6ae0ce9abe3ab`

![window-circular](window-circular/image.png)

## multigroup-default

- status: `ok`
- faces: 34 -- geometry_hash: `fa48d09e828515c2`

![multigroup-default](multigroup-default/image.png)

## multigroup-fills

- status: `ok`
- faces: 63 -- geometry_hash: `6461d74b0b613ec3`

![multigroup-fills](multigroup-fills/image.png)

## balcony-posts-wall

- status: `contract violated`
- faces: 6 -- geometry_hash: `696a9cb143dee764`
- problems: ["missing/empty matgroups: ['railing_posts']"] (known: ['balcony_railing_untagged'])

![balcony-posts-wall](balcony-posts-wall/image.png)

## balcony-rails-wall

- status: `contract violated`
- faces: 6 -- geometry_hash: `696a9cb143dee764`
- problems: ["missing/empty matgroups: ['railing_rails']"] (known: ['balcony_railing_untagged'])

![balcony-rails-wall](balcony-rails-wall/image.png)

## balcony-wallfill-wall

- status: `contract violated`
- faces: 6 -- geometry_hash: `696a9cb143dee764`
- problems: ["missing/empty matgroups: ['railing_walls']"] (known: ['balcony_railing_untagged'])

![balcony-wallfill-wall](balcony-wallfill-wall/image.png)

## balcony-inner-curved

- status: `contract violated`
- faces: 50 -- geometry_hash: `ae77a2dcde0752f2`
- problems: ["missing/empty matgroups: ['railing_posts']"] (known: ['balcony_railing_untagged', 'grouped_balcony_curved_platform'])

![balcony-inner-curved](balcony-inner-curved/image.png)

## stairs-filled

- status: `ok`
- faces: 206 -- geometry_hash: `f49fca28353759a8`

![stairs-filled](stairs-filled/image.png)

## stairs-blocked

- status: `ok`
- faces: 209 -- geometry_hash: `b3674892e3b71201`

![stairs-blocked](stairs-blocked/image.png)

## stairs-slope

- status: `ok`
- faces: 207 -- geometry_hash: `d7740a83db49826d`

![stairs-slope](stairs-slope/image.png)

## stairs-no-landing

- status: `ok`
- faces: 101 -- geometry_hash: `cb46a1a9010fa196`

![stairs-no-landing](stairs-no-landing/image.png)

## fill-panels

- status: `ok`
- faces: 29 -- geometry_hash: `6228abc314f25fce`

![fill-panels](fill-panels/image.png)

## fill-glass-panes

- status: `ok`
- faces: 29 -- geometry_hash: `769e1826c0ea22ad`

![fill-glass-panes](fill-glass-panes/image.png)

## fill-louver

- status: `ok`
- faces: 70 -- geometry_hash: `069641f4e6ef1582`

![fill-louver](fill-louver/image.png)

## fill-bar

- status: `ok`
- faces: 12 -- geometry_hash: `38efe1d061bc8d47`

![fill-bar](fill-bar/image.png)
