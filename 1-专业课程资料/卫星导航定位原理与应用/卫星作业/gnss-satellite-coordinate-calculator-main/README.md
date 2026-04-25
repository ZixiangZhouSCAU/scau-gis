# GNSS卫星坐标计算器

**项目英文名称：** `gnss-satellite-coordinate-calculator`

## 项目简介

GNSS卫星坐标计算器是一个基于Python和Tkinter开发的图形化应用程序，用于从GPS广播星历（RINEX格式）文件中提取轨道参数，并根据指定的观测时间计算卫星在地心地固坐标系（ECEF）中的三维坐标。

### 主要功能

- **星历文件解析**：自动解析RINEX 2格式的GPS导航文件，提取所有必要的轨道参数（包括开普勒轨道根数、摄动参数等）
- **坐标计算**：根据IS-GPS-200标准，实现完整的GPS卫星坐标计算流程，包括：
  - 平均角速度计算
  - 平近点角计算
  - 开普勒方程迭代求解（偏近点角）
  - 真近点角计算
  - 摄动改正（轨道面内、径向、倾角方向）
  - 地心地固坐标系转换
- **距离计算**：自动计算卫星与地心的距离
- **图形界面**：提供友好的中文图形界面，支持：
  - 默认文件和时间快速加载
  - 手动文件选择
  - 观测时间输入和验证
  - 卫星选择
  - 参数和结果的表格化显示
  - 滚动查看所有内容

### 应用场景

- GNSS数据处理和教学
- 卫星轨道分析
- GPS定位算法验证
- 导航系统开发和研究

### 技术栈

- **编程语言**：Python 3.7+
- **GUI框架**：Tkinter (ttk)
- **核心库**：标准库（math, os, re, datetime, tkinter）
- **数据格式**：RINEX 2 导航文件格式
- **计算标准**：IS-GPS-200 GPS接口控制文档

### 系统要求

- Python 3.7 或更高版本
- Tkinter（通常随Python安装，macOS可能需要额外安装python-tk）
- 支持的操作系统：Windows、macOS、Linux

### 快速开始

#### 方式一：使用Conda（推荐）

1. **安装Conda**（如果尚未安装）
   - 下载并安装 [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 或 [Anaconda](https://www.anaconda.com/products/distribution)

2. **创建Conda环境**
   ```bash
   # 使用environment.yml文件创建环境（推荐）
   conda env create -f environment.yml
   
   # 或者手动创建环境
   conda create -n gnss-calculator python=3.10 tk
   ```

3. **激活环境**
   ```bash
   conda activate gnss-calculator
   ```

4. **准备星历文件**
   - 将GPS广播星历文件（.n格式）放入 `nav/` 文件夹

5. **运行程序**
   ```bash
   python app/gui_gnss.py
   ```

6. **退出环境**（使用完毕后）
   ```bash
   conda deactivate
   ```

#### 方式二：使用系统Python

1. 克隆或下载本项目
2. 将GPS广播星历文件（.n格式）放入 `nav/` 文件夹
3. 运行程序：
   ```bash
   python3 app/gui_gnss.py
   ```
4. 在GUI界面中选择卫星并输入观测时间，点击"计算坐标"即可

## 程序说明

本程序用于根据GPS广播星历文件计算卫星在地心地固坐标系(ECEF)中的坐标。

## 文件夹结构

```
GNSS小程序/
├── app/
│   └── gui_gnss.py          # 主程序文件
├── nav/                      # 星历文件存放目录
│   └── GPS_Broadcast_Ephemeris_RINEX.n  # GPS广播星历文件（请将.n文件放在此目录）
├── environment.yml           # Conda环境配置文件
└── README.md                 # 本说明文件
```

## 使用说明

### 1. 星历文件准备

**重要：请将GPS广播星历文件（.n格式）放在 `nav/` 文件夹内！**

- 默认文件：`nav/GPS_Broadcast_Ephemeris_RINEX.n`
- 如果使用其他文件，请将文件复制到 `nav/` 文件夹中
- 程序支持RINEX 2格式的GPS导航文件（.n或.N扩展名）

### 2. 运行程序

**使用Conda环境（推荐）：**
```bash
conda activate gnss-calculator
python app/gui_gnss.py
```

**使用系统Python：**
```bash
python3 app/gui_gnss.py
```

### 3. 程序功能

- **默认文件**：程序会自动加载 `nav/GPS_Broadcast_Ephemeris_RINEX.n`（如果存在）
- **默认时间**：默认观测时间为 `2023-09-09 00:00:09` UTC
- **手动选择**：可以点击"选择文件"按钮选择其他星历文件
- **参数提取**：自动从星历文件中提取所有GPS轨道参数
- **坐标计算**：根据提取的参数和观测时间计算卫星ECEF坐标

### 4. 操作步骤

1. 启动程序后，如果默认文件存在，会自动加载
2. 选择要计算的卫星（下拉菜单）
3. 确认或修改观测时间（UTC格式：YYYY-MM-DD HH:MM:SS）
4. 点击"计算坐标"按钮
5. 查看计算结果：
   - "提取的参数"表格：显示从星历文件中提取的所有参数
   - "卫星地心地固坐标"表格：显示计算得到的X、Y、Z坐标（单位：米）

## 注意事项

1. **文件位置**：必须将.n文件放在 `nav/` 文件夹中，程序才能正确读取
2. **文件格式**：仅支持RINEX 2格式的GPS导航文件，不支持GLONASS格式（.g文件）
3. **观测时间**：建议使用星历参考历元(toe)附近的时间，最佳范围为toe前后2小时内
4. **坐标范围**：GPS卫星坐标通常在±20000km范围内，如果计算结果异常，请检查：
   - 文件是否正确
   - 观测时间是否合理
   - 星历文件是否过期

## 技术说明

- 程序按照IS-GPS-200标准实现GPS卫星坐标计算
- 使用RINEX 2格式解析广播星历参数
- 计算过程包括：开普勒方程求解、摄动改正、坐标转换等步骤
- 所有计算公式和参数提取位置已在代码中详细标注

## 文件路径说明

- 程序使用**相对路径**存储和显示文件路径
- 文件路径显示为相对于 `GNSS小程序` 目录的相对路径（如：`nav/GPS_Broadcast_Ephemeris_RINEX.n`）
- 程序会自动将相对路径转换为绝对路径进行文件读取
- 这样可以确保程序在不同电脑上都能正常运行

## 更新日志

- 支持默认文件和默认时间
- 自动加载默认星历文件
- 使用相对路径，提高程序可移植性
- 改进参数提取算法，修复字段边界问题
- 优化界面显示，使用表格显示坐标

