# SWAT+ HRU Processor

GUI and command-line helper for making smaller SWAT+ TxtInOut runs from selected HRU IDs. The original TxtInOut folder is used as the source; the tool creates a copied working folder and rewrites files inside that copy.

## What It Creates

For one HRU, the output folder is created inside the selected source directory as:

```text
solo_<hru_id>
```

For more than one HRU, the output folder is:

```text
multi_<YYYYMMDD_HHMMSS>
```

If a matching `solo_<hru_id>` folder already exists, it is replaced. The copy skips common generated output files such as `*.out`, `*.fin`, `*.sqlite`, `*.db`, `*.log`, `*.pid`, `fort.*`, `*.txt`, and `*.csv`.

## Modes

### Isolated HRU Mode

This is the default mode when `Keep Routing` is off.

The tool keeps only the selected HRU rows and removes routing from those HRUs. This is useful when you want a small isolated HRU-only run.

Files rewritten in the generated output folder:

- `hru.con`: keeps selected HRUs, renumbers HRU IDs from `1`, remaps the `props` pointer, and sets the routing target count to `0`.
- `hru-data.hru`: keeps the referenced HRU data rows and renumbers their first-column IDs from `1`.
- `ls_unit.ele`: keeps landscape-unit elements for the selected HRUs and remaps their HRU pointers.
- `ls_unit.def`: keeps landscape-unit definitions that still reference retained elements.
- `rout_unit.ele`: keeps routing-unit elements for the selected HRUs and remaps their HRU pointers.
- `rout_unit.def`: keeps routing-unit definitions that still reference retained route elements.
- `rout_unit.rtu`: keeps routing-unit data rows that still match retained routing-unit definitions.
- `object.cnt`: sets the object total to the selected HRU count and zeros the other supported object counts.
- `file.cio`: replaces routed and non-HRU connection filenames with `null`, including routing units, channels, aquifers, reservoirs, recalls, outlets, delratio, water allocation, object print, HRU-LTE, and related connection files.
- `print.prt`: disables routing-unit and landscape-unit print rows that are not valid after routing is removed: `lsunit_wb`, `lsunit_nb`, `lsunit_ls`, `lsunit_pw`, `ru`, `ru_salt`, and `ru_cs`.

### Routed Mode

Turn on `Keep Routing` to preserve the downstream routing chain from the selected HRUs.

The tool finds the routing units containing the selected HRUs, traces downstream through the SWAT+ connectivity graph, keeps every reachable object, filters those files, and renumbers IDs so SWAT+ arrays still line up.

Files that can be rewritten when their object type is kept:

- `hru.con` and `hru-data.hru`
- `rout_unit.con` and `rout_unit.rtu`
- `chandeg.con` and `channel-lte.cha`
- `channel.con` and `channel.cha`
- `aquifer.con` and `aquifer.aqu`
- `reservoir.con` and `reservoir.res`
- `recall.con` and `recall.rec`
- `exco.con`
- `delratio.con`
- `outlet.con`
- `rout_unit.ele`
- `rout_unit.def`
- `ls_unit.ele`
- `ls_unit.def`
- `object.cnt`
- `file.cio`

In routed mode, `file.cio` keeps connection and data files for retained object types and sets unneeded object types to `null`. It always nullifies `water_allocation.wro`, `element.wro`, `water_rights.wro`, and `object.prt` for subset runs.

Routed mode does not disable the routing-unit rows in `print.prt`; those outputs remain available because routing units are still present.

## Running From The Exe

The current packaged executable is:

```text
dist\swat_processor\swat_processor.exe
```

Use the GUI to:

1. Select the source TxtInOut directory.
2. Enter one HRU ID or enable `Multiple HRUs` and enter values such as `1,4-6,10`.
3. Leave `Keep Routing` off for isolated HRU mode, or turn it on for routed mode.
4. Turn on `Run SWAT+ Simulation` only when you want the generated folder to run immediately.
5. Click `Modify HRU`.

If simulation is enabled and more than one `.exe` is found in the source directory, the GUI asks which executable to run.

## Running From Source

Install dependencies:

```powershell
py -3.12 -m pip install -r requirements.txt
```

Run the GUI:

```powershell
py -3.12 SRC\gui\gui_main.py
```

Run the test suite:

```powershell
py -3.12 -m pytest tests -q
```

Build the Windows executable:

```powershell
$env:PYTHONPATH=''
py -3.12 -m PyInstaller --noconfirm --clean gui_main.spec
```

## Core Modules

- `SRC/core/swat_main.py`: main processing entry point.
- `SRC/core/FileModifier.py`: isolated-mode file rewrites.
- `SRC/core/RoutingTracer.py`: routed-mode tracing, filtering, and renumbering.
- `SRC/core/object_counts.py`: header-aware `object.cnt` count updates.
- `SRC/core/TxtinoutReader.py`: TxtInOut copy and SWAT+ execution support.
- `SRC/core/FileReader.py`: SWAT+ table reading helper.
- `SRC/gui/gui_logic.py`: GUI controller.
- `SRC/gui/gui_layout.py`: GUI layout.

## Important Notes

The source TxtInOut files are not rewritten directly. The generated `solo_*` or `multi_*` folder is the working copy that changes.

Routed mode is only as complete as the connectivity files in the source TxtInOut folder. If a selected HRU routes to object types that are missing from the source, those missing files cannot be reconstructed.

Generated simulation outputs can be large and are ignored by git.
