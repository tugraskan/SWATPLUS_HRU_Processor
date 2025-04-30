from PyInstaller.utils.hooks import collect_submodules

# Define the main script
main_script = 'SRC/gui/gui_main.py'

# Add the path to the `SRC` directory
pathex = ['.', 'SRC']

# Collect hidden imports (submodules in `core` and `gui`)
hidden_imports = collect_submodules('core') + collect_submodules('gui')

# Add data files to be included in the executable
datas = [
    ('SRC/core', 'core'),
    ('SRC/gui', 'gui'),
    ('SRC', 'SRC')
]

# Build the analysis
a = Analysis(
    [main_script],
    pathex=pathex,
    binaries=[],
    datas=datas,  # Add data files manually if needed
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

# Build the Python Zip archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='swat_processor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Change to False for a windowed app
)

# Collect all binaries and files for final packaging
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='swat_processor',
)
