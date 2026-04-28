# PyInstaller spec for the light Eternego binary.
#
# Eternego loads many modules dynamically via pkgutil.iter_modules — meanings,
# abilities, business specs. PyInstaller's static analysis can't see those, so
# we enumerate them explicitly here as hiddenimports.
#
# Run: pyinstaller eternego.spec
# Output:
#   - Linux:   dist/eternego                 (single binary)
#   - Windows: dist/eternego.exe             (single binary)
#   - macOS:   dist/eternego                 (CLI binary)
#              dist/Eternego.app             (app bundle, double-click target)

import os
import glob
import sys


def collect_modules(directory: str, package: str) -> list[str]:
    """Return import paths for every .py module under `directory`, excluding __init__."""
    out = []
    for path in sorted(glob.glob(os.path.join(directory, '*.py'))):
        name = os.path.splitext(os.path.basename(path))[0]
        if name == '__init__':
            continue
        out.append(f'{package}.{name}')
    return out


hiddenimports = []
hiddenimports += collect_modules('application/core/brain/meanings', 'application.core.brain.meanings')
hiddenimports += collect_modules('application/core/brain/functions', 'application.core.brain.functions')
hiddenimports += collect_modules('application/core/abilities', 'application.core.abilities')
hiddenimports += collect_modules('application/business/persona', 'application.business.persona')
hiddenimports += collect_modules('application/business/environment', 'application.business.environment')
hiddenimports += collect_modules('application/business/routine', 'application.business.routine')
hiddenimports += [
    'application.platform.OS',
    'application.platform.filesystem',
    'application.platform.http',
    'application.platform.telegram',
    'application.platform.discord',
    'application.platform.web',
    'application.platform.anthropic',
    'application.platform.openai',
    'application.platform.ollama',
]


a = Analysis(
    ['index.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('web/ui', 'web/ui'),
        ('assets', 'assets'),
        ('config', 'config'),
        ('shells', 'shells'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'torch', 'transformers', 'peft', 'trl', 'datasets', 'accelerate',
        'bitsandbytes', 'gguf', 'numpy', 'sentencepiece', 'protobuf',
    ],
)

pyz = PYZ(a.pure, a.zipped_data)

icon_path = None
if sys.platform == 'darwin' and os.path.exists('build/icon/eternego.icns'):
    icon_path = 'build/icon/eternego.icns'
elif sys.platform == 'win32' and os.path.exists('build/icon/eternego.ico'):
    icon_path = 'build/icon/eternego.ico'

# Two build modes selected via ETERNEGO_BUILD_TARGET:
#   - "cli" (default)  → onefile console binary — Linux/Windows release + macOS CLI artifact
#   - "app"            → onedir windowed binary wrapped in macOS .app bundle. PyInstaller 6+
#                        silently drops data files in onefile + .app combos, so .app must be onedir.
build_target = os.environ.get('ETERNEGO_BUILD_TARGET', 'cli')
is_app = build_target == 'app'

if is_app and sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='eternego',
        debug=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        icon=icon_path,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='eternego',
    )
    app = BUNDLE(
        coll,
        name='Eternego.app',
        icon=icon_path,
        bundle_identifier='ai.eternego.eternego',
        version='0.1.0',
        info_plist={
            'CFBundleName': 'Eternego',
            'CFBundleDisplayName': 'Eternego',
            'CFBundleShortVersionString': '0.1.0',
            'NSHighResolutionCapable': True,
            'LSBackgroundOnly': False,
            'LSUIElement': False,
            'LSEnvironment': {'ETERNEGO_LAUNCH_FROM_BUNDLE': '1'},
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='eternego',
        debug=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,
        console=True,
        disable_windowed_traceback=False,
        icon=icon_path,
    )
