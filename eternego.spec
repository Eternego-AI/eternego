# PyInstaller spec for the light Eternego binary.
#
# Eternego loads many modules dynamically via pkgutil.iter_modules — meanings,
# abilities, business specs. PyInstaller's static analysis can't see those, so
# we enumerate them explicitly here as hiddenimports.
#
# Run: pyinstaller eternego.spec
# Output: dist/eternego (single binary on Linux, .app on macOS, .exe on Windows)

import os
import glob


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
)
