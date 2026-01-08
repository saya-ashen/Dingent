# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import platform

# --- 基础名称配置 ---
system_name = platform.system().lower()
machine_name = platform.machine().lower()
base_name = f"dingent-{system_name}-{machine_name}"

# 单文件输出名称 (例如: dingent-windows-amd64.exe)
exe_name_onefile = base_name
if system_name == 'windows':
    exe_name_onefile += ".exe"

# 单目录文件夹名称 (例如: dingent-windows-amd64_dir)
dir_name_onefolder = base_name + "_dir"

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

static = [('static.tar.gz','build/static.tar.gz','DATA')]

# --- 1. 共享分析 (Analysis) ---
# 这一步对于两种模式是通用的，只需要执行一次
a = Analysis(
    ["src/dingent/cli/cli.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
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

# --- 2. 共享 PYZ ---
pyz = PYZ(a.pure)

# =============================================================================
# 模式 A: OneFolder (单目录模式)
# 逻辑: 生成一个不包含依赖的 exe，然后用 COLLECT 把所有东西收集到一个文件夹中
# =============================================================================

exe_folder = EXE(
    pyz,
    a.scripts,
    [], # 注意：这里不包含 binaries 和 datas，它们在 COLLECT 中收集
    exclude_binaries=True, # 关键：排除二进制文件，只保留引导程序
    name='dingent', # 文件夹内部的可执行文件名称 (通常简短即可)
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_folder,
    a.binaries,
    a.zipfiles,
    a.datas + static, # 静态资源在这里添加
    strip=False,
    upx=True,
    upx_exclude=[],
    name=dir_name_onefolder, # 生成的文件夹名称 (dist/dingent-xxx_dir)
)

# =============================================================================
# 模式 B: OneFile (单文件模式)
# 逻辑: 将 binaries, zipfiles, datas 全部塞进 EXE 中
# =============================================================================

exe_file = EXE(
    pyz,
    a.scripts,
    a.binaries,       # 包含二进制
    a.zipfiles,       # 包含 zip
    a.datas + static, # 包含数据
    [],
    name=exe_name_onefile, # 生成的单文件名 (dist/dingent-xxx.exe)
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
