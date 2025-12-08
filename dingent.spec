# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import copy_metadata

from PyInstaller.building.build_main import Analysis, PYZ, EXE, Tree

block_cipher = None

datas = []
binaries = []
hiddenimports = []

hiddenimports +=[
'litellm.litellm_core_utils.tokenizers',
'tiktoken_ext',
'tiktoken_ext.openai_public',
]

datas += collect_data_files("cookiecutter")
datas += collect_data_files('litellm')
tmp_ret = collect_all("nodejs_wheel")
datas += tmp_ret[0]
datas += copy_metadata('fastmcp')
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
dingent_hidden_imports = collect_submodules('dingent')
hiddenimports += dingent_hidden_imports

static = [('src/dingent/static.tar.gz','build/static.tar.gz','DATA')]


a = Analysis(
    ["src/dingent/cli/cli.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,  # 这里现在包含了 static_tree 的所有内容
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas + static,
    [],
    name="dingent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
