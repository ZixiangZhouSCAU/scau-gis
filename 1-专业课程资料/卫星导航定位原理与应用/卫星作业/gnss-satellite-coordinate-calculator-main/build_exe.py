#!/usr/bin/env python3
"""
OrbitVision Pro 打包脚本
使用PyInstaller将程序打包成独立的exe文件
"""
import PyInstaller.__main__
import os

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(current_dir, 'app', 'gui_gnss.py')
nav_path = os.path.join(current_dir, 'nav')
icon_path = os.path.join(current_dir, 'icon.ico')  # 如果有图标文件

# PyInstaller打包参数
args = [
    app_path,                           # 主程序文件
    '--name=OrbitVision Pro',           # 生成的exe名称
    '--onefile',                        # 打包成单个exe文件
    '--windowed',                       # 不显示控制台窗口
    '--clean',                          # 清理临时文件
    f'--add-data={nav_path};nav',       # 包含nav文件夹
    '--hidden-import=matplotlib',       # 确保matplotlib被包含
    '--hidden-import=numpy',            # 确保numpy被包含
    '--hidden-import=tkinter',          # 确保tkinter被包含
    '--hidden-import=matplotlib.backends.backend_tkagg',
    '--hidden-import=mpl_toolkits.mplot3d',
    '--collect-all=matplotlib',         # 收集matplotlib所有文件
    '--noupx',                          # 不使用UPX压缩(避免某些问题)
    '--exclude-module=PyQt5',           # 排除PyQt5
    '--exclude-module=PyQt6',           # 排除PyQt6
    '--exclude-module=PySide2',         # 排除PySide2
    '--exclude-module=PySide6',         # 排除PySide6
    '--exclude-module=pygame',          # 排除pygame(不需要)
    '--exclude-module=IPython',         # 排除IPython(减小体积)
    '--exclude-module=jedi',            # 排除jedi(减小体积)
    '--exclude-module=parso',           # 排除parso(减小体积)
]

# 如果图标文件存在，添加图标参数
if os.path.exists(icon_path):
    args.append(f'--icon={icon_path}')

print("=" * 60)
print("OrbitVision Pro - 开始打包")
print("=" * 60)
print(f"主程序: {app_path}")
print(f"包含数据: {nav_path}")
print("打包模式: 单文件exe (--onefile)")
print("窗口模式: 无控制台 (--windowed)")
print("=" * 60)

# 执行打包
PyInstaller.__main__.run(args)

print("\n" + "=" * 60)
print("打包完成!")
print("生成的exe文件位置: dist/OrbitVision Pro.exe")
print("=" * 60)
