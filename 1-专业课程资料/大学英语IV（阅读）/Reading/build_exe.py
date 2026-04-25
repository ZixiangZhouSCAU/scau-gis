"""
使用PyInstaller打包英语阅读刷题软件为exe文件
运行方式: python build_exe.py
"""

import os
import sys
import subprocess
import shutil

def install_pyinstaller():
    """安装PyInstaller"""
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装")
        return True
    except ImportError:
        print("📦 正在安装 PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller 安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller 安装失败: {e}")
            return False

def clean_build_folders():
    """清理之前的构建文件"""
    folders_to_clean = ['build', 'dist', '__pycache__']
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"🧹 已清理文件夹: {folder}")
    
    # 清理spec文件
    spec_files = [f for f in os.listdir('.') if f.endswith('.spec')]
    for spec_file in spec_files:
        os.remove(spec_file)
        print(f"🧹 已清理文件: {spec_file}")

def build_exe():
    """构建exe文件"""
    print("🚀 开始构建exe文件...")
    
    # PyInstaller命令参数
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包成单个exe文件
        "--windowed",                   # 无控制台窗口
        "--name=英语阅读刷题软件",        # 指定exe文件名
        "--icon=icon.ico",              # 图标文件(如果存在)
        "--add-data=客观题题库.md;.",     # 包含题库文件
        "--optimize=2",                 # 优化级别
        "--strip",                      # 去除调试信息
        "--exclude-module=matplotlib",   # 排除不需要的模块
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=PIL",
        "--exclude-module=cv2",
        "test.py"                       # 主程序文件
    ]
    
    try:
        # 检查是否有图标文件，没有的话移除icon参数
        if not os.path.exists("icon.ico"):
            cmd.remove("--icon=icon.ico")
            print("ℹ️  未找到icon.ico文件，将使用默认图标")
        
        # 执行打包命令
        subprocess.check_call(cmd)
        print("✅ exe文件构建成功！")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        return False

def create_icon():
    """创建简单的图标文件"""
    icon_content = '''
# 这里可以放置ico文件内容，或者使用在线工具生成ico文件
# 可以从以下网站免费生成ico文件：
# https://www.favicon-generator.org/
# https://convertio.co/png-ico/
'''
    
    if not os.path.exists("icon.ico"):
        print("💡 提示：您可以在当前目录放置一个icon.ico文件作为程序图标")

def optimize_exe():
    """优化exe文件"""
    dist_path = "dist"
    if os.path.exists(dist_path):
        exe_files = [f for f in os.listdir(dist_path) if f.endswith('.exe')]
        if exe_files:
            exe_path = os.path.join(dist_path, exe_files[0])
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"📊 exe文件大小: {file_size:.2f} MB")
            print(f"📁 exe文件位置: {os.path.abspath(exe_path)}")

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 英语阅读刷题软件 - exe打包工具")
    print("=" * 60)
    
    # 检查是否在正确的目录
    if not os.path.exists("test.py"):
        print("❌ 错误：未找到test.py文件，请确保在正确的目录运行此脚本")
        return
    
    # 1. 安装PyInstaller
    if not install_pyinstaller():
        return
    
    # 2. 清理之前的构建文件
    clean_build_folders()
    
    # 3. 创建图标提示
    create_icon()
    
    # 4. 构建exe
    if build_exe():
        # 5. 优化和显示信息
        optimize_exe()
        print("\n" + "=" * 60)
        print("🎉 打包完成！")
        print("📁 exe文件位置: dist/英语阅读刷题软件.exe")
        print("💡 提示：首次运行可能较慢，这是正常现象")
        print("=" * 60)
    else:
        print("\n❌ 打包失败，请检查错误信息")

if __name__ == "__main__":
    main()

