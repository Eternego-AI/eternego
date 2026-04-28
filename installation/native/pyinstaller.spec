# PyInstaller spec for the light Eternego binary.
#
# Eternego loads many modules dynamically via pkgutil.iter_modules — meanings,
# abilities, business specs. PyInstaller's static analysis can't see those, so
# we enumerate them explicitly here as hiddenimports.
#
# Run from repo root: pyinstaller installation/native/pyinstaller.spec
# Output:
#   - Linux:   dist/eternego                 (single binary)
#   - Windows: dist/eternego.exe             (single binary)
#   - macOS:   dist/eternego                 (CLI binary)
#              dist/Eternego.app             (app bundle, double-click target)

import os
import glob
import sys

# PyInstaller resolves spec-relative paths (scripts, datas, icons) from the
# spec file's directory, not the working directory. The spec lives in
# installation/native/, so anchor everything off the repo root.
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
REPO_ROOT = os.path.abspath(os.path.join(SPEC_DIR, '..', '..'))


def collect_modules(rel_directory: str, package: str) -> list[str]:
    """Return import paths for every .py module under `rel_directory` (relative to repo root)."""
    abs_directory = os.path.join(REPO_ROOT, rel_directory)
    out = []
    for path in sorted(glob.glob(os.path.join(abs_directory, '*.py'))):
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

# Tray icon (macOS .app + Windows .exe only). Linux AppImage and Docker
# don't ship pystray and never import cli/desktop.py — see index.py.
if sys.platform == 'darwin':
    hiddenimports += ['pystray._darwin']
elif sys.platform == 'win32':
    hiddenimports += ['pystray._win32']


a = Analysis(
    [os.path.join(REPO_ROOT, 'index.py')],
    pathex=[REPO_ROOT],
    binaries=[],
    datas=[
        (os.path.join(REPO_ROOT, 'web/ui'), 'web/ui'),
        (os.path.join(REPO_ROOT, 'assets'), 'assets'),
        (os.path.join(REPO_ROOT, 'config'), 'config'),
        (os.path.join(REPO_ROOT, 'installation/shells'), 'shells'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'torch', 'transformers', 'peft', 'trl', 'datasets', 'accelerate',
        'bitsandbytes', 'gguf', 'numpy', 'sentencepiece', 'protobuf',
    ] + (
        # Tray launcher is darwin/win32 only — keep its imports out of the
        # Linux AppImage so PyInstaller doesn't fail trying to resolve pystray.
        ['desktop', 'pystray', 'PIL'] if sys.platform not in ('darwin', 'win32') else []
    ),
)

pyz = PYZ(a.pure, a.zipped_data)

icon_path = None
darwin_icon = os.path.join(REPO_ROOT, 'build/icon/eternego.icns')
windows_icon = os.path.join(REPO_ROOT, 'build/icon/eternego.ico')
if sys.platform == 'darwin' and os.path.exists(darwin_icon):
    icon_path = darwin_icon
elif sys.platform == 'win32' and os.path.exists(windows_icon):
    icon_path = windows_icon

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
            # launchd hands GUI apps a sparse PATH (/usr/bin:/bin:/usr/sbin:/sbin)
            # — extend it so subprocess calls find brew, ollama, git, etc.
            'LSEnvironment': {
                'ETERNEGO_LAUNCH_FROM_BUNDLE': '1',
                'PATH': '/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
            },
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
