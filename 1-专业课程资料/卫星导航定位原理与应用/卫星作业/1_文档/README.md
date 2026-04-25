# GNSS OrbitMaster

科研级GNSS卫星位置解算工具，支持广播星历 (RINEX NAV) 与精密星历 (SP3) 双模式，并提供 PyQt6 高分辨率友好界面。

## 功能特性
- 广播星历解算：遵循 IS-GPS-200 算法链条，完整实现开普勒迭代与摄动改正。
- 精密星历插值：基于 `scipy.interpolate.BarycentricInterpolator` 的按需拉格朗日插值，支持任意历元。
- 统一计算引擎：自动识别文件类型并缓存星历，提供对比模式输出。
- 科技风GUI：高DPI适配、文件管理、参数配置、结果表格展示及状态反馈。
- 线程化执行：解算逻辑运行于 `QThread`，保障界面响应。

## 环境准备
```powershell
# 建议使用虚拟环境
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```
> 如遇镜像网络问题，可考虑预先下载 `georinex`, `astropy`, `scipy`, `PyQt6` 的离线包。

## 运行
```powershell
cd 1_文档
python main_app.py
```
程序启动后：
1. 通过“星历文件管理”加载 NAV (*.??n, *.nav) 或 SP3 (*.sp3) 文件（可从 IGS/GA/WHU FTP 获取样例数据）。
2. 在“计算参数”中选择卫星、设置 UTC 时间及星历类型/对比模式。
3. 点击“执行计算”，右侧表格将展示坐标结果；状态栏显示执行反馈。

## 打包
使用 PyInstaller 进行单文件分发时，需显式包含 `georinex` 等数据资源：
```powershell
cd 1_文档
pyinstaller main_app.py --name "GNSS OrbitMaster" --noconfirm --add-data "C:/Python/Lib/site-packages/georinex;georinex"
```
请根据实际 Python 安装路径调整 `--add-data` 参数。

## 目录结构
```
1_文档/
├── broadcast_solver.py
├── engine.py
├── main_app.py
├── precise_solver.py
├── models.py
├── time_utils.py
├── requirements.txt
└── README.md
```

## 数据提示
- 广播星历：IGS 发布的 `brdc`/`igrg` 系列 RINEX NAV。
- 精密星历：IGS 精密轨道 `igs*.sp3`、`igr*.sp3` 等。

如需进一步扩展（滤波、PPP、批处理等），可在 `engine.py` 基础上添加新解算器并在 GUI 中挂载。祝使用愉快！
