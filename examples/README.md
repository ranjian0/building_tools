# Examples gallery

Every example is a complete-building rule file. Browse by directory
(residential / commercial / civic / industrial / special / pipelines) or
list them from the CLI:

```bash
btools examples list --json
btools examples run residential.suburban-house
```

Run any file directly:

```bash
btools run examples/residential/suburban-house.py --render confirm.png
```

See docs/RULES.md for the full `ctx` vocabulary.
