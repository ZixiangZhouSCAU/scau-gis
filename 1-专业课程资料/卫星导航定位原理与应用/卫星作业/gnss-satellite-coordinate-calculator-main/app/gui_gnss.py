#!/usr/bin/env python3
import sys
import math
import os
import re
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timezone, timedelta
import csv
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d import Axes3D
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


MU = 3.986005e14  # m^3/s^2
OMEGA_E = 7.292115e-5  # rad/s, Earth rotation rate


def parse_float(s: str) -> float:
    return float(s.replace('D', 'E').replace('d', 'e'))


def read_file(path: str) -> list[str]:
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()


def split_header_body(lines: list[str]):
    header, body = [], []
    end = False
    for ln in lines:
        (header if not end else body).append(ln)
        if not end and 'END OF HEADER' in ln:
            end = True
    return header, body


def get_leap_seconds(header: list[str]) -> int:
    for ln in header:
        if 'LEAP SECONDS' in ln:
            try:
                return int(ln[:6])
            except Exception:
                return 18
    return 18


def parse_epoch_tokens(tokens: list[str]) -> datetime:
    yy = int(tokens[0]); year = 1900 + yy if yy >= 80 else 2000 + yy
    mo = int(tokens[1]); da = int(tokens[2])
    hh = int(tokens[3]); mm = int(tokens[4]); ss = int(float(tokens[5]))
    return datetime(year, mo, da, hh, mm, ss, tzinfo=timezone.utc)


def extract_gps_ephemeris(body: list[str]):
    """
    ====================================================================================
    从RINEX 2格式GPS导航文件中提取卫星广播星历参数
    RINEX 2格式: 每颗卫星占8行数据，每行80个字符
    ====================================================================================
    """
    ephs = []
    i = 0
    while i + 7 < len(body):
        seg = body[i:i+8]  # 提取一颗卫星的8行数据块
        i += 8
        
        # ============================================================================
        # 【参数提取 - 第1行(seg[0)]】卫星号和时钟参数
        # RINEX 2格式第1行结构: 
        #   列1-2: 卫星号(PRN, 2位数字)
        #   列3-22: 年(2位), 月, 日, 时, 分, 秒 (历元时间toc)
        #   列23-41: af0 (卫星钟差, 单位: 秒)
        #   列42-60: af1 (卫星钟速, 单位: 秒/秒)
        #   列61-79: af2 (卫星钟漂, 单位: 秒/秒²)
        # ============================================================================
        prn_raw = seg[0][0:2].strip()  # <-- 【PRN提取】从第1行前2列提取卫星号
        if not prn_raw:
            continue
        # GPS satellites are in RINEX 2 often without 'G' prefix
        if prn_raw.startswith('R') or prn_raw.startswith('E'):
            # skip non-GPS
            continue
        try:
            prn = f"G{int(prn_raw):02d}"  # <-- 【PRN格式化】转换为G01, G02等格式
        except ValueError:
            continue
        
        # <-- 【toc提取】从第1行第3列开始提取历元时间(年,月,日,时,分,秒)
        tks = seg[0][2:]  # 跳过前2列(卫星号)，提取剩余部分
        nums = re.findall(r'[+-]?\d+(?:\.\d*)?(?:[DEde][+-]?\d+)?', tks)  # 提取所有数字(支持科学计数法D/E格式)
        if len(nums) < 8:
            continue
        try:
            # <-- 【toc解析】前6个数字组成历元时间: 年(2位), 月, 日, 时, 分, 秒
            toc = parse_epoch_tokens(nums[:6])
            # <-- 【af0提取】第7个数字: 卫星钟差 (单位: 秒)
            af0 = parse_float(nums[6])
            # <-- 【af1提取】第8个数字: 卫星钟速 (单位: 秒/秒)
            af1 = parse_float(nums[7])
            # <-- 【af2提取】第9个数字(如果存在): 卫星钟漂 (单位: 秒/秒²)
            af2 = parse_float(nums[8]) if len(nums) > 8 else 0.0
        except (ValueError, IndexError):
            continue

        def four(ln: str):
            """
            ====================================================================================
            从RINEX 2格式的一行中提取4个参数
            RINEX 2格式: 每行从第4列(索引3)开始，每19个字符为一个字段，共4个字段
            列位置: 3-22, 22-41, 41-60, 60-79 (每个字段19个字符宽)
            修正: 使用正则表达式从整行提取所有数字，避免字段边界问题
            ====================================================================================
            """
            # 从第4列(索引3)开始，提取所有科学计数法数字（支持D/E格式）
            # 这样可以避免字段边界导致的数字截断问题
            line_content = ln[3:].strip()  # 跳过前3列
            # 提取所有完整的科学计数法数字
            numbers = re.findall(r'[+-]?\d+(?:\.\d+)?(?:[DEde][+-]?\d+)?', line_content)
            # 取前4个数字，如果不足4个则用0.0填充
            while len(numbers) < 4:
                numbers.append('0.0')
            return [parse_float(n) for n in numbers[:4]]  # 转换为浮点数

        try:
            # ============================================================================
            # 【参数提取 - 第2行(seg[1])】轨道参数1
            # 列3-22: IODE (星历表数据龄期, 无单位)
            # 列22-41: Crs (卫星矢径的正弦调和项改正振幅, 单位: 米)
            # 列41-60: Δn (平均角速度差, 单位: 弧度/秒)
            # 列60-79: M0 (参考历元的平近点角, 单位: 弧度)
            # ============================================================================
            IODE, Crs, DeltaN, M0 = four(seg[1])
            # <-- 【IODE提取】从第2行第1个字段提取
            # <-- 【Crs提取】从第2行第2个字段提取
            # <-- 【DeltaN提取】从第2行第3个字段提取 (公式中的Δn)
            # <-- 【M0提取】从第2行第4个字段提取 (公式中的M0)
            
            # ============================================================================
            # 【参数提取 - 第3行(seg[2])】轨道参数2
            # 列3-22: Cuc (升交距角的余弦调和项改正振幅, 单位: 弧度)
            # 列22-41: e (轨道第一偏心率, 无单位)
            # 列41-60: Cus (升交距角的正弦调和项改正振幅, 单位: 弧度)
            # 列60-79: √A (轨道半长轴的平方根, 单位: 米^0.5) <-- 【公式中的A来源】
            # ============================================================================
            Cuc, e, Cus, sqrtA = four(seg[2])
            # <-- 【Cuc提取】从第3行第1个字段提取
            # <-- 【e提取】从第3行第2个字段提取 (公式中的偏心率e)
            # <-- 【Cus提取】从第3行第3个字段提取
            # <-- 【sqrtA提取】从第3行第4个字段提取 (公式中的√A, 用于计算 a = (√A)²)
            
            # ============================================================================
            # 【参数提取 - 第4行(seg[3])】轨道参数3
            # 列3-22: Toe (星历表参考历元, 单位: GPS周内秒) <-- 【公式中的toe来源】
            # 列22-41: Cic (轨道倾角的余弦调和项改正振幅, 单位: 弧度)
            # 列41-60: Ω0 (参考历元的升交点赤经, 单位: 弧度) <-- 【公式中的Ω0来源】
            # 列60-79: Cis (轨道倾角的正弦调和项改正振幅, 单位: 弧度)
            # ============================================================================
            Toe, Cic, Omega0, Cis = four(seg[3])
            # <-- 【Toe提取】从第4行第1个字段提取 (公式中的toe, 用于计算 tk = t - toe)
            # <-- 【Cic提取】从第4行第2个字段提取
            # <-- 【Omega0提取】从第4行第3个字段提取 (公式中的Ω0)
            # <-- 【Cis提取】从第4行第4个字段提取
            
            # ============================================================================
            # 【参数提取 - 第5行(seg[4])】轨道参数4
            # 列3-22: i0 (参考历元的轨道倾角, 单位: 弧度) <-- 【公式中的i0来源】
            # 列22-41: Crc (卫星矢径的余弦调和项改正振幅, 单位: 米)
            # 列41-60: ω (近地点角距, 单位: 弧度) <-- 【公式中的ω来源】
            # 列60-79: Ω̇ (升交点赤经变化率, 单位: 弧度/秒) <-- 【公式中的Ω̇来源】
            # ============================================================================
            i0, Crc, omega, OmegaDot = four(seg[4])
            # <-- 【i0提取】从第5行第1个字段提取 (公式中的i0)
            # <-- 【Crc提取】从第5行第2个字段提取
            # <-- 【omega提取】从第5行第3个字段提取 (公式中的ω, 近地点角距)
            # <-- 【OmegaDot提取】从第5行第4个字段提取 (公式中的Ω̇)
            
            # ============================================================================
            # 【参数提取 - 第6行(seg[5])】轨道参数5
            # 列3-22: IDOT (轨道倾角变化率, 单位: 弧度/秒) <-- 【公式中的IDOT来源】
            # 列22-41: (保留字段, 通常为0)
            # 列41-60: (保留字段, 通常为0)
            # 列60-79: (保留字段, 通常为0)
            # ============================================================================
            IDOT, _, _, _ = four(seg[5])
            # <-- 【IDOT提取】从第6行第1个字段提取 (公式中的IDOT)
            # 后3个字段通常为0或保留，不使用
            
        except (ValueError, IndexError) as ex:
            continue

        # ============================================================================
        # 【参数存储】将所有提取的参数存储到字典中，供后续计算使用
        # ============================================================================
        ephs.append({
            'prn': prn,      # 卫星号 (G01, G02, ...)
            'toc': toc,      # 历元时间 (datetime对象)
            'af0': af0,      # 卫星钟差 (秒)
            'af1': af1,      # 卫星钟速 (秒/秒)
            'af2': af2,      # 卫星钟漂 (秒/秒²)
            'IODE': IODE,    # 星历表数据龄期
            'Crs': Crs,      # 卫星矢径的正弦调和项改正振幅 (米)
            'DeltaN': DeltaN,  # 平均角速度差 (弧度/秒) <-- 用于公式 n = n0 + Δn
            'M0': M0,        # 参考历元的平近点角 (弧度) <-- 用于公式 Mk = M0 + n·tk
            'Cuc': Cuc,      # 升交距角的余弦调和项改正振幅 (弧度)
            'e': e,          # 轨道第一偏心率 <-- 用于开普勒方程和真近点角计算
            'Cus': Cus,      # 升交距角的正弦调和项改正振幅 (弧度)
            'sqrtA': sqrtA,  # 轨道半长轴的平方根 (米^0.5) <-- 用于公式 a = (√A)²
            'Toe': Toe,      # 星历表参考历元 (GPS周内秒) <-- 用于公式 tk = t - toe
            'Cic': Cic,      # 轨道倾角的余弦调和项改正振幅 (弧度)
            'Omega0': Omega0,  # 参考历元的升交点赤经 (弧度) <-- 用于公式 Lk = Ω0 + (Ω̇ - ωe)·tk - ωe·toe
            'Cis': Cis,      # 轨道倾角的正弦调和项改正振幅 (弧度)
            'i0': i0,        # 参考历元的轨道倾角 (弧度) <-- 用于公式 ik = i0 + IDOT·tk + δi
            'Crc': Crc,      # 卫星矢径的余弦调和项改正振幅 (米)
            'omega': omega,  # 近地点角距 (弧度) <-- 用于公式 Φk = Vk + ω
            'OmegaDot': OmegaDot,  # 升交点赤经变化率 (弧度/秒) <-- 用于公式 Lk = Ω0 + (Ω̇ - ωe)·tk - ωe·toe
            'IDOT': IDOT     # 轨道倾角变化率 (弧度/秒) <-- 用于公式 ik = i0 + IDOT·tk + δi
        })
    return ephs


def utc_to_gps_seconds_of_week(dt_utc: datetime, leap_seconds: int) -> tuple[int, float]:
    gps_epoch = datetime(1980, 1, 6, tzinfo=timezone.utc)
    # GPS time = UTC + leap_seconds
    dt_gps = dt_utc + timedelta(seconds=leap_seconds)
    delta = dt_gps - gps_epoch
    total_seconds = delta.total_seconds()
    week = int(total_seconds // 604800)
    sow = total_seconds - week * 604800
    return week, sow


def normalize_tk(tk: float) -> float:
    # wrap to [-302400, 302400]
    half = 302400.0
    while tk > half:
        tk -= 604800.0
    while tk < -half:
        tk += 604800.0
    return tk


def normalize_angle(x: float) -> float:
    # wrap angle to [-pi, pi]
    x = (x + math.pi) % (2.0 * math.pi) - math.pi
    return x


def compute_gps_ecef(e: dict, t_obs_utc: datetime, leap_seconds: int):
    """
    ====================================================================================
    计算GPS卫星在地心地固坐标系(ECEF)中的坐标
    按照RINEX 2格式GPS广播星历参数计算，参考IS-GPS-200标准
    ====================================================================================
    """
    
    # ============================================================================
    # 【步骤1】计算轨道半长轴 a (单位: m)
    # 公式: a = (√A)²
    # <-- 【A的使用】A来自星历参数sqrtA，在extract_gps_ephemeris函数中从RINEX文件提取
    # ============================================================================
    a = e['sqrtA'] * e['sqrtA']  # <-- e['sqrtA'] 是从RINEX文件第3行提取的√A值
    
    # ============================================================================
    # 【步骤2】计算平均角速度 n0 和修正后的平均角速度 n (单位: rad/s)
    # 公式(4.27): n0 = √(μ / a³) 其中 μ = 3.986005×10¹⁴ m³/s² (地球引力常数)
    # 公式(4.28): n = n0 + Δn  (Δn 是星历中给出的摄动修正值)
    # ============================================================================
    n0 = math.sqrt(MU / (a ** 3))
    n = n0 + e['DeltaN']
    
    # ============================================================================
    # 【步骤3】计算归化时间 tk (单位: s)
    # 公式(4.29): tk = t - toe
    # <-- 【t的使用】t是观测时间，从GUI界面输入框获取，格式为UTC时间
    # 其中: t_obs_utc 是用户输入的UTC观测时间，通过utc_to_gps_seconds_of_week转换为GPS周内秒(sow)
    #       toe 是星历参考历元(从星历中读取的Toe参数，单位: GPS周内秒)
    # 注意: tk 需要归一化到 [-302400, 302400] 秒范围内(±0.5周)
    # ============================================================================
    _, sow = utc_to_gps_seconds_of_week(t_obs_utc, leap_seconds)  # <-- t转换为GPS周内秒
    tk = normalize_tk(sow - e['Toe'])  # <-- tk = t - toe，其中t=sow(观测时刻GPS周内秒)，toe=e['Toe'](星历参考历元)

    # ============================================================================
    # 【步骤4】计算观测时刻的平近点角 Mk (单位: rad)
    # 公式(4.30): Mk = M0 + n·tk
    # 其中: M0 是参考历元toe时的平近点角(从星历中读取)
    # ============================================================================
    Mk = e['M0'] + n * tk

    # ============================================================================
    # 【步骤5】计算偏近点角 Ek (单位: rad) - 迭代求解开普勒方程
    # 公式(4.31): Ek = Mk + e·sin(Ek)  (开普勒方程，需迭代求解)
    # 迭代方法: Ek^(i+1) = Mk + e·sin(Ek^(i))
    # 初始值: Ek^(0) = Mk
    # 收敛条件: |Ek^(i+1) - Ek^(i)| < 1e-12
    # 注意: GPS卫星轨道偏心率e很小(约0.01)，通常2-3次迭代即可收敛
    # ============================================================================
    Ek = Mk
    for _ in range(10):
        Ek_next = Mk + e['e'] * math.sin(Ek)
        if abs(Ek_next - Ek) < 1e-12:
            Ek = Ek_next; break
        Ek = Ek_next

    # ============================================================================
    # 【步骤6】计算真近点角 Vk (单位: rad)
    # 公式(4.32): 
    #   cos(Vk) = (cos(Ek) - e) / (1 - e·cos(Ek))
    #   sin(Vk) = (√(1-e²)·sin(Ek)) / (1 - e·cos(Ek))
    # 公式(4.33): Vk = arctan(sin(Vk), cos(Vk))
    # ============================================================================
    sin_vk = math.sqrt(1 - e['e']**2) * math.sin(Ek) / (1 - e['e'] * math.cos(Ek))
    cos_vk = (math.cos(Ek) - e['e']) / (1 - e['e'] * math.cos(Ek))
    Vk = math.atan2(sin_vk, cos_vk)

    # ============================================================================
    # 【步骤7】计算升交距角(未修正的纬度幅角) Φk (单位: rad)
    # 公式(4.34): Φk = Vk + ω
    # 其中: ω 是近地点角距(argument of perigee, 从星历中读取)
    # ============================================================================
    Phi = Vk + e['omega']

    # ============================================================================
    # 【步骤8】计算摄动改正项 δu, δr, δi
    # 公式(4.26): 
    #   δu = Cus·sin(2Φk) + Cuc·cos(2Φk)  (升交距角改正, 单位: rad)
    #   δr = Crs·sin(2Φk) + Crc·cos(2Φk)  (卫星矢径改正, 单位: m)
    #   δi = Cis·sin(2Φk) + Cic·cos(2Φk)  (轨道倾角改正, 单位: rad)
    # 其中: Cus, Cuc, Crs, Crc, Cis, Cic 是星历中给出的6个调和改正振幅
    # ============================================================================
    du = e['Cus'] * math.sin(2*Phi) + e['Cuc'] * math.cos(2*Phi)
    dr = e['Crs'] * math.sin(2*Phi) + e['Crc'] * math.cos(2*Phi)
    di = e['Cis'] * math.sin(2*Phi) + e['Cic'] * math.cos(2*Phi)

    # ============================================================================
    # 【步骤9】计算经摄动改正后的升交距角、卫星矢径和轨道倾角
    # 公式(4.35):
    #   uk = Φk + δu  (修正后的升交距角, 单位: rad)
    #   rk = a·(1 - e·cos(Ek)) + δr  (修正后的卫星矢径, 单位: m)
    #   ik = i0 + IDOT·tk + δi  (修正后的轨道倾角, 单位: rad)
    # 其中: i0 是参考历元时的轨道倾角, IDOT 是轨道倾角变化率
    # ============================================================================
    u = normalize_angle(Phi + du)  # 归一化到[-π, π]以提高数值稳定性
    r = a * (1 - e['e'] * math.cos(Ek)) + dr
    i_k = e['i0'] + e['IDOT'] * tk + di

    # ============================================================================
    # 【步骤10】计算卫星在轨道平面坐标系中的坐标 (单位: m)
    # 公式(4.36):
    #   xk = rk·cos(uk)
    #   yk = rk·sin(uk)
    #   zk = 0  (轨道平面内z坐标为0)
    # 坐标系定义: x轴指向升交点方向, y轴与x轴垂直形成右手系, z轴垂直于轨道平面
    # ============================================================================
    x_prime = r * math.cos(u)
    y_prime = r * math.sin(u)

    # ============================================================================
    # 【步骤11】计算观测时刻t的升交点大地经度 Lk (单位: rad)
    # 公式(4.43): Lk = Ω0 + (Ω̇ - ωe)·tk
    # 其中: 
    #   Ω0 是参考历元toe时的升交点赤经(从星历中读取, 单位: rad)
    #   Ω̇ 是升交点赤经变化率(从星历中读取, 单位: rad/s)
    #   ωe = 7.292115×10⁻⁵ rad/s (地球自转角速度)
    #   tk = t - toe (归化时间)
    # 注意: 这里计算的是地固坐标系中的升交点经度，考虑了地球自转
    # 修正: 根据GPS ICD-200标准，公式中不需要 -ωe·toe 项，因为toe已经包含在tk的计算中
    # ============================================================================
    Omega_k = e['Omega0'] + (e['OmegaDot'] - OMEGA_E) * tk
    # 归一化到[0, 2π]范围
    Omega_k = Omega_k % (2.0 * math.pi)

    # ============================================================================
    # 【步骤12】计算卫星在地心地固坐标系(ECEF/WGS-84)中的坐标 (单位: m)
    # 公式(4.46): 通过旋转矩阵将轨道平面坐标转换到ECEF坐标系
    #   X = xk·cos(Lk) - yk·cos(ik)·sin(Lk)
    #   Y = xk·sin(Lk) + yk·cos(ik)·cos(Lk)
    #   Z = yk·sin(ik)
    # 坐标系: WGS-84地心地固坐标系, 原点在地心, Z轴指向北极, X轴指向本初子午线与赤道交点
    # ============================================================================
    X = x_prime * math.cos(Omega_k) - y_prime * math.cos(i_k) * math.sin(Omega_k)
    Y = x_prime * math.sin(Omega_k) + y_prime * math.cos(i_k) * math.cos(Omega_k)
    Z = y_prime * math.sin(i_k)
    
    return X, Y, Z, {
        'a': a, 'n0': n0, 'n': n, 'tk': tk, 'Mk': Mk, 'Ek': Ek, 'Vk': Vk,
        'Phi': Phi, 'u': u, 'r': r, 'i': i_k, 'Omega_k': Omega_k
    }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('🛰️ OrbitVision Pro - 卫星轨道可视化分析系统')
        self.configure(bg='#050b18')
        self.scale_factor = 1.0
        self._apply_scaling()
        self._configure_styles()

        # 设置默认文件路径（相对于程序所在目录）
        # 程序结构: GNSS小程序/app/gui_gnss.py
        # 星历文件放在: GNSS小程序/nav/GPS_Broadcast_Ephemeris_RINEX.22n
        
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe运行
            # PyInstaller将数据解压到sys._MEIPASS
            base_path = sys._MEIPASS
            root_dir = base_path
            nav_dir = os.path.join(base_path, 'nav')
        else:
            # 如果是脚本运行
            script_dir = os.path.dirname(os.path.abspath(__file__))  # app目录
            root_dir = os.path.dirname(script_dir)  # GNSS小程序目录
            nav_dir = os.path.join(root_dir, 'nav')  # nav文件夹
            
        self.default_file = os.path.join(nav_dir, 'GPS_Broadcast_Ephemeris_RINEX.22n')
        self.default_time = '2023-09-09 00:00:09'
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        # 2K屏幕优化窗口尺寸 - 增加宽度以容纳3D可视化
        if screen_w >= 2400:
            window_w = min(int(screen_w * 0.85), 2200)
            window_h = min(int(screen_h * 0.85), 1400)
        else:
            window_w = min(int(screen_w * 0.9), 1800)
            window_h = min(int(screen_h * 0.85), 1100)
        self.geometry(f'{window_w}x{window_h}')
        self.minsize(1000, 750)
        
        # 使用相对路径显示（相对于GNSS小程序目录）
        if os.path.exists(self.default_file):
            # 显示相对路径 nav/GPS_Broadcast_Ephemeris_RINEX.22n
            rel_path = os.path.relpath(self.default_file, root_dir)
            self.file_path = tk.StringVar(value=rel_path)
        else:
            self.file_path = tk.StringVar(value='')
        self.obs_time = tk.StringVar(value=self.default_time)  # 默认观测时间
        self.leap_seconds = 18
        self.ephs = []
        
        # 保存根目录和nav目录路径，用于路径转换
        self.root_dir = root_dir
        self.nav_dir = nav_dir
        
        # 3D可视化相关变量
        self.fig_3d = None
        self.ax_3d = None
        self.canvas_3d = None

        self._build_ui()
        
        # 绑定变量变化事件，用于检测用户是否修改了默认值
        self.file_path.trace_add('write', self._on_file_changed)
        self.obs_time.trace_add('write', self._on_time_changed)
        
        # 如果默认文件存在，自动加载星历
        if os.path.exists(self.default_file):
            self.after(100, self.auto_load_default)  # 延迟100ms后自动加载，确保UI已完全初始化

    def _apply_scaling(self):
        """Scale widgets for hi-DPI/2K displays."""
        # 启用DPI感知
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            pass
        
        screen_w = max(1, self.winfo_screenwidth())
        screen_h = max(1, self.winfo_screenheight())
        
        # 2K屏幕优化：2560x1440或类似分辨率
        if screen_w >= 2400 or screen_h >= 1350:
            self.scale_factor = 1.5  # 2K屏幕使用1.5倍缩放
        elif screen_w >= 1900 or screen_h >= 1050:
            self.scale_factor = 1.25  # 1080p+使用1.25倍
        else:
            self.scale_factor = 1.0  # 普通屏幕
        
        # 应用Tk缩放
        try:
            self.tk.call('tk', 'scaling', self.scale_factor * 1.4)
        except tk.TclError:
            pass
        
        self.section_pad = int(18 * self.scale_factor)
        self.widget_pad = int(12 * self.scale_factor)
        self.row_gap = int(8 * self.scale_factor)

    def _configure_styles(self):
        """Create the neon tech ttk theme."""
        self.base_bg = '#050b18'
        self.panel_bg = '#0c1d38'
        self.card_bg = '#0f2243'
        self.accent = '#00e0ff'
        self.text_primary = '#e6f2ff'
        self.text_muted = '#8aa0c7'
        self.entry_bg = '#0b1931'
        self.tree_bg = '#071427'
        self.tree_sel = '#173c66'

        style = ttk.Style()
        try:
            if 'tech_dark' not in style.theme_names():
                style.theme_create('tech_dark', parent='clam', settings={
                    'TFrame': {'configure': {'background': self.panel_bg}},
                    'TLabel': {'configure': {'background': self.panel_bg, 'foreground': self.text_primary}},
                    'TNotebook': {'configure': {'background': self.panel_bg}},
                    'TNotebook.Tab': {'configure': {'background': self.card_bg}},
                })
            style.theme_use('tech_dark')
        except tk.TclError:
            pass

        # 2K屏幕字体尺寸优化
        title_size = int(24 * self.scale_factor)
        body_size = int(12 * self.scale_factor)
        small_size = int(10 * self.scale_factor)
        mono_size = int(14 * self.scale_factor)  # 表格字体加大到14
        label_size = int(11 * self.scale_factor)
        # 中文使用微软雅黑，西文使用Times New Roman
        self.font_title = tkfont.Font(family='Microsoft YaHei UI', size=title_size, weight='bold')
        self.font_body = tkfont.Font(family='Microsoft YaHei UI', size=body_size)
        self.font_small = tkfont.Font(family='Microsoft YaHei UI', size=small_size)
        self.font_mono = tkfont.Font(family='Times New Roman', size=mono_size)
        self.font_label = tkfont.Font(family='Microsoft YaHei UI', size=label_size, weight='bold')
        self.option_add('*Font', self.font_body)

        style.configure('TechOuter.TFrame', background=self.base_bg)
        style.configure('TechCard.TFrame', background=self.card_bg, relief='flat')
        style.configure('TechCard.TLabelframe', background=self.card_bg, relief='solid', borderwidth=1)
        style.configure('TechCard.TLabelframe.Label', background=self.card_bg, foreground=self.accent, font=self.font_label)
        style.configure('Tech.TLabel', background=self.card_bg, foreground=self.text_primary, font=self.font_body)
        style.configure('TechHint.TLabel', background=self.card_bg, foreground=self.text_muted, font=self.font_small)
        style.configure('TechTitle.TLabel', background=self.base_bg, foreground=self.accent, font=self.font_title)
        style.configure('TechSection.TLabel', background=self.card_bg, foreground=self.accent, font=self.font_label, weight='bold')
        btn_pad_x = int(14 * self.scale_factor)
        btn_pad_y = int(10 * self.scale_factor)
        style.configure('TechAccent.TButton', background=self.accent, foreground=self.base_bg, 
                        font=self.font_body, padding=(btn_pad_x, btn_pad_y), relief='flat', borderwidth=0)
        style.map('TechAccent.TButton', 
                  background=[('active', '#08b6d2'), ('pressed', '#07aac0')],
                  relief=[('pressed', 'sunken')])
        style.configure('TechGhost.TButton', background=self.card_bg, foreground=self.accent, 
                        font=self.font_body, padding=(btn_pad_x-2, btn_pad_y-2), relief='flat', borderwidth=1)
        style.map('TechGhost.TButton', 
                  background=[('active', '#132a4e'), ('pressed', '#0f2447')],
                  foreground=[('active', '#00f0ff')],
                  relief=[('pressed', 'sunken')])
        style.configure('TechInput.TEntry', fieldbackground=self.entry_bg, background=self.entry_bg,
                        foreground=self.text_primary, borderwidth=1, relief='solid',
                        insertcolor=self.accent, selectbackground=self.accent, selectforeground=self.base_bg)
        style.configure('Tech.TCombobox', fieldbackground=self.entry_bg, background=self.entry_bg,
                        foreground=self.text_primary, arrowcolor=self.accent, borderwidth=1, relief='solid')
        style.map('Tech.TCombobox', 
                  fieldbackground=[('readonly', self.entry_bg)],
                  background=[('readonly', self.entry_bg), ('active', '#0f2447')],
                  bordercolor=[('focus', self.accent)])
        row_height = int(42 * self.scale_factor)  # 增加行高以适应更大的字体
        style.configure('Tech.Treeview', background=self.tree_bg, fieldbackground=self.tree_bg,
                        foreground=self.text_primary, rowheight=row_height, 
                        font=self.font_mono, borderwidth=1, relief='solid')
        style.map('Tech.Treeview', 
                  background=[('selected', self.tree_sel)], 
                  foreground=[('selected', '#ffffff')])
        style.configure('Tech.Treeview.Heading', background=self.card_bg, foreground=self.accent,
                        relief='flat', font=self.font_body, borderwidth=1)
        # 滚动条样式 - 红色主题
        style.configure('Tech.Vertical.TScrollbar', background='#ff0000', troughcolor='#2a0000', 
                        arrowcolor='#ffffff', bordercolor='#ff0000', relief='flat')
        style.map('Tech.Vertical.TScrollbar', 
                  background=[('active', '#ff4d4d'), ('pressed', '#cc0000')])
        self.option_add('*TCombobox*Listbox.background', self.entry_bg)
        self.option_add('*TCombobox*Listbox.foreground', self.text_primary)
        self.option_add('*TCombobox*Listbox.font', self.font_body)
        self.option_add('*insertBackground', self.accent)
        self.option_add('*Foreground', self.text_primary)

    def _build_ui(self):
        # 主容器 - 使用PanedWindow实现可调节的左右分割
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=8, 
                              bg=self.base_bg, sashrelief=tk.RAISED, 
                              bd=0, handlesize=10)
        paned.pack(fill='both', expand=True)
        
        # 左侧控制面板容器
        left_container = ttk.Frame(paned, style='TechOuter.TFrame')
        paned.add(left_container, minsize=550, stretch='never')
        
        # 右侧可视化面板容器
        right_container = ttk.Frame(paned, style='TechCard.TFrame')
        paned.add(right_container, minsize=400, stretch='always')
        
        # 设置初始分割位置
        self.after(100, lambda: paned.sash_place(0, 600, 0))

        # 左侧面板内容（带滚动）
        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(left_container, highlightthickness=0, borderwidth=0, background=self.base_bg)
        scrollbar = ttk.Scrollbar(left_container, orient='vertical', command=canvas.yview, style='Tech.Vertical.TScrollbar')
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 增加底部padding，确保内容不被遮挡
        scrollable_frame = ttk.Frame(canvas, style='TechOuter.TFrame', padding=(self.section_pad, self.section_pad, self.section_pad, self.section_pad * 4))

        def _on_frame_configure(event):
            # 确保滚动区域包含整个frame
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            # 调整frame宽度以适应canvas
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind('<Configure>', _on_canvas_configure)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            if event.widget == canvas or str(event.widget).startswith(str(canvas)):
                delta = 0
                if event.delta:
                    delta = int(-1 * (event.delta / 120))
                elif event.num == 4:
                    delta = -1
                elif event.num == 5:
                    delta = 1
                if delta:
                    canvas.yview_scroll(delta, "units")

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<Button-4>", _on_mousewheel)
        scrollable_frame.bind("<Button-5>", _on_mousewheel)

        self.canvas = canvas
        self.scrollable_frame = scrollable_frame
        
        # 标题区域
        self._create_header(scrollable_frame)
        
        # 各个功能区块
        self._create_file_section(scrollable_frame)
        self._create_time_section(scrollable_frame)
        self._create_sat_section(scrollable_frame)
        self._create_params_section(scrollable_frame)
        self._create_results_section(scrollable_frame)
        self._create_advanced_section(scrollable_frame)

        # 初始化右侧可视化面板
        self._init_3d_panel(right_container)
        
        # 存储计算结果用于批量计算和导出
        self.batch_results = []
        
        # 初始化提示标签的显示状态
        self.after(50, self._update_default_hints)
        self.after(100, self._update_scroll_region)

    def _create_header(self, parent):
        frame = ttk.Frame(parent, style='TechOuter.TFrame')
        frame.pack(fill='x', pady=(0, self.row_gap * 2))
        
        ttk.Label(frame, text='🛰️ OrbitVision Pro', style='TechTitle.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Satellite Orbit Visualization & Analysis System', style='TechHint.TLabel').pack(anchor='w')

    def _create_section_frame(self, parent, title):
        frame = ttk.LabelFrame(parent, text=title, style='TechCard.TLabelframe', padding=self.widget_pad)
        frame.pack(fill='x', pady=(0, self.row_gap * 2))
        return frame

    def _create_file_section(self, parent):
        frame = self._create_section_frame(parent, '导航文件设置')
        
        # Grid layout
        frame.columnconfigure(1, weight=1)
        
        ttk.Label(frame, text='文件路径:', style='Tech.TLabel').grid(row=0, column=0, sticky='w', padx=(0, self.widget_pad))
        ttk.Entry(frame, textvariable=self.file_path, style='TechInput.TEntry').grid(row=0, column=1, sticky='ew', padx=(0, self.widget_pad))
        ttk.Button(frame, text='选择文件', command=self.choose_file, style='TechGhost.TButton').grid(row=0, column=2, sticky='e')
        
        self.lbl_default_file = ttk.Label(frame, text='默认文件', style='TechHint.TLabel')
        self.lbl_default_file.grid(row=1, column=1, sticky='w', pady=(5, 0))
        
        self.lbl_manual_hint = ttk.Label(frame, text='如需使用其他文件，请点击选择文件手动添加', style='TechHint.TLabel')
        self.lbl_manual_hint.grid(row=2, column=1, sticky='w')

    def _create_time_section(self, parent):
        frame = self._create_section_frame(parent, '观测时间设置')
        frame.columnconfigure(1, weight=1)
        
        ttk.Label(frame, text='UTC时间:', style='Tech.TLabel').grid(row=0, column=0, sticky='w', padx=(0, self.widget_pad))
        ttk.Entry(frame, textvariable=self.obs_time, style='TechInput.TEntry').grid(row=0, column=1, sticky='ew', padx=(0, self.widget_pad))
        ttk.Label(frame, text='格式: YYYY-MM-DD HH:MM:SS', style='TechHint.TLabel').grid(row=0, column=2, sticky='e')
        
        self.lbl_default_time = ttk.Label(frame, text='默认时间', style='TechHint.TLabel')
        self.lbl_default_time.grid(row=1, column=1, sticky='w', pady=(5, 0))
        
        self.lbl_time_format_hint = ttk.Label(frame, text='必须严格按照右边的格式填写观测时间', style='TechHint.TLabel')
        self.lbl_time_format_hint.grid(row=2, column=1, sticky='w')

    def _create_sat_section(self, parent):
        frame = self._create_section_frame(parent, '卫星选择与操作')
        frame.columnconfigure(1, weight=1)
        
        # Row 0: Selection and Parse
        ttk.Label(frame, text='选择卫星:', style='Tech.TLabel').grid(row=0, column=0, sticky='w', padx=(0, self.widget_pad))
        self.cbo_sv = ttk.Combobox(frame, state='readonly', style='Tech.TCombobox')
        self.cbo_sv.grid(row=0, column=1, sticky='ew', padx=(0, self.widget_pad))
        ttk.Button(frame, text='解析星历', command=self.load_nav, style='TechAccent.TButton').grid(row=0, column=2, sticky='e')
        
        # Row 1: Action Buttons
        btn_frame = ttk.Frame(frame, style='TechCard.TFrame')
        btn_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(self.row_gap * 2, 0))
        
        ttk.Button(btn_frame, text='计算单颗卫星', command=self.calculate, style='TechAccent.TButton').pack(side='left', fill='x', expand=True, padx=(0, self.widget_pad))
        ttk.Button(btn_frame, text='批量计算所有', command=self.calculate_all, style='TechAccent.TButton').pack(side='left', fill='x', expand=True, padx=(0, self.widget_pad))
        ttk.Button(btn_frame, text='导出结果', command=self.export_results, style='TechGhost.TButton').pack(side='left', fill='x', expand=True)

    def _create_params_section(self, parent):
        frame = self._create_section_frame(parent, '星历参数详情')
        
        self.tree = ttk.Treeview(frame, columns=('k','v'), show='headings', height=10, style='Tech.Treeview')
        self.tree.heading('k', text='参数', anchor='center')
        self.tree.heading('v', text='数值', anchor='center')
        self.tree.column('k', width=int(150 * self.scale_factor), anchor='center')
        self.tree.column('v', width=int(350 * self.scale_factor), anchor='center')
        
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview, style='Tech.Vertical.TScrollbar')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _create_results_section(self, parent):
        frame = self._create_section_frame(parent, '计算结果 (ECEF)')
        
        # XYZ Treeview
        ttk.Label(frame, text='坐标分量:', style='Tech.TLabel').pack(anchor='w', pady=(0, 5))
        self.tree_xyz = ttk.Treeview(frame, columns=('axis','value_m','value_km'), show='headings', height=4, style='Tech.Treeview')
        self.tree_xyz.heading('axis', text='坐标轴')
        self.tree_xyz.heading('value_m', text='数值 (m)')
        self.tree_xyz.heading('value_km', text='数值 (km)')
        
        col_w = int(180 * self.scale_factor)
        self.tree_xyz.column('axis', width=int(80 * self.scale_factor), anchor='center')
        self.tree_xyz.column('value_m', width=col_w, anchor='center')
        self.tree_xyz.column('value_km', width=col_w, anchor='center')
        self.tree_xyz.pack(fill='x', pady=(0, self.row_gap))
        
        # Distance Treeview
        ttk.Label(frame, text='地心距离:', style='Tech.TLabel').pack(anchor='w', pady=(0, 5))
        self.tree_distance = ttk.Treeview(frame, columns=('axis','value_m','value_km'), show='headings', height=1, style='Tech.Treeview')
        self.tree_distance.heading('axis', text='项目')
        self.tree_distance.heading('value_m', text='数值 (m)')
        self.tree_distance.heading('value_km', text='数值 (km)')
        self.tree_distance.column('axis', width=int(80 * self.scale_factor), anchor='center')
        self.tree_distance.column('value_m', width=col_w, anchor='center')
        self.tree_distance.column('value_km', width=col_w, anchor='center')
        self.tree_distance.pack(fill='x')

    def _create_advanced_section(self, parent):
        frame = self._create_section_frame(parent, '高级功能')
        
        btn_frame = ttk.Frame(frame, style='TechCard.TFrame')
        btn_frame.pack(fill='x')
        
        ttk.Button(btn_frame, text='卫星轨迹预测', command=self.predict_trajectory, style='TechGhost.TButton').pack(side='left', fill='x', expand=True)

    def _update_scroll_region(self):
        """更新canvas的滚动区域"""
        if hasattr(self, 'canvas') and hasattr(self, 'scrollable_frame'):
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _init_3d_panel(self, parent):
        """初始化右侧3D可视化面板"""
        if not HAS_MATPLOTLIB:
            # 如果没有matplotlib，显示提示信息
            ttk.Label(parent, text='3D可视化功能需要matplotlib库', 
                     style='TechSection.TLabel').pack(pady=20)
            ttk.Label(parent, text='请运行: pip install matplotlib', 
                     style='TechHint.TLabel').pack()
            return
        
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        import numpy as np
        import matplotlib.pyplot as plt
        
        # 设置matplotlib中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        
        # 标题
        title_frame = ttk.Frame(parent, style='TechCard.TFrame')
        title_frame.pack(fill='x', pady=(0, 5))
        ttk.Label(title_frame, text='🌍 实时卫星轨道3D视图', 
                 style='TechSection.TLabel').pack(side='left')
        ttk.Label(title_frame, text='批量计算后自动更新', 
                 style='TechHint.TLabel').pack(side='right')
        
        # 创建Figure - 进一步减小尺寸
        self.fig_3d = Figure(figsize=(5, 4.5), facecolor='white', dpi=85)
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d', facecolor='white')
        
        # 绘制初始地球
        self._draw_earth()
        
        # 设置初始标题
        self.ax_3d.set_xlabel('X (km)', fontsize=9, weight='bold', color='navy', fontproperties='Microsoft YaHei')
        self.ax_3d.set_ylabel('Y (km)', fontsize=9, weight='bold', color='navy', fontproperties='Microsoft YaHei')
        self.ax_3d.set_zlabel('Z (km)', fontsize=9, weight='bold', color='navy', fontproperties='Microsoft YaHei')
        self.ax_3d.set_title('等待卫星数据加载...\n请先进行批量计算', 
                            fontsize=11, weight='bold', color='gray', pad=10, fontproperties='Microsoft YaHei')
        self.ax_3d.grid(True, linestyle=':', alpha=0.3, linewidth=0.5)
        self.ax_3d.set_box_aspect([1,1,1])
        self.ax_3d.view_init(elev=20, azim=45)
        
        # 创建画布
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=parent)
        self.canvas_3d.draw()
        
        # 添加工具栏
        toolbar_frame = ttk.Frame(parent, style='TechCard.TFrame')
        toolbar_frame.pack(side='top', fill='x', pady=(0, 3))
        toolbar = NavigationToolbar2Tk(self.canvas_3d, toolbar_frame)
        toolbar.update()
        
        self.canvas_3d.get_tk_widget().pack(fill='both', expand=True)
        
        # 状态栏
        self.status_3d = ttk.Label(parent, text='就绪 | 可使用鼠标旋转、缩放视图', 
                                   style='TechHint.TLabel')
        self.status_3d.pack(side='bottom', fill='x', pady=(3, 0))

    def _draw_earth(self):
        """绘制地球"""
        import numpy as np
        
        # 清除之前的内容
        self.ax_3d.clear()
        
        # 绘制地球
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, np.pi, 25)
        earth_radius = 6371  # 地球半径(公里)
        x_earth = earth_radius * np.outer(np.cos(u), np.sin(v))
        y_earth = earth_radius * np.outer(np.sin(u), np.sin(v))
        z_earth = earth_radius * np.outer(np.ones(np.size(u)), np.cos(v))
        
        self.ax_3d.plot_surface(x_earth, y_earth, z_earth, color='#1e90ff', alpha=0.3, 
                               edgecolor='#4169e1', linewidth=0.1, antialiased=True)
        
        # 绘制赤道
        theta = np.linspace(0, 2 * np.pi, 100)
        eq_x = earth_radius * np.cos(theta)
        eq_y = earth_radius * np.sin(theta)
        eq_z = np.zeros_like(theta)
        self.ax_3d.plot(eq_x, eq_y, eq_z, color='#00cc00', linewidth=1.5, alpha=0.5)
        
        # 绘制本初子午线
        phi = np.linspace(0, 2 * np.pi, 100)
        pm_x = earth_radius * np.cos(phi)
        pm_y = np.zeros_like(phi)
        pm_z = earth_radius * np.sin(phi)
        self.ax_3d.plot(pm_x, pm_y, pm_z, color='#cc0000', linewidth=1.5, alpha=0.5)
        
        # 地心标记
        self.ax_3d.scatter([0], [0], [0], c='red', s=100, marker='o', 
                          edgecolors='darkred', linewidths=1.5, alpha=0.8)

    def update_3d_view(self):
        """更新3D视图显示卫星"""
        if not HAS_MATPLOTLIB or self.ax_3d is None:
            return
        
        import numpy as np
        
        # 重新绘制地球
        self._draw_earth()
        
        if not self.batch_results:
            self.ax_3d.set_title('等待卫星数据加载...\n请先进行批量计算', 
                                fontsize=11, weight='bold', color='gray', pad=10, fontproperties='Microsoft YaHei')
        else:
            # 绘制卫星
            xs = [r['X']/1000 for r in self.batch_results]
            ys = [r['Y']/1000 for r in self.batch_results]
            zs = [r['Z']/1000 for r in self.batch_results]
            
            # 卫星点
            self.ax_3d.scatter(xs, ys, zs, c='#ff6b00', s=150, marker='*', 
                              edgecolors='yellow', linewidths=1.5, alpha=0.9, 
                              depthshade=True)
            
            # 连线
            for i in range(len(xs)):
                self.ax_3d.plot([0, xs[i]], [0, ys[i]], [0, zs[i]], 
                               color='cyan', linestyle='--', linewidth=0.4, alpha=0.25)
            
            # 标签
            for i, r in enumerate(self.batch_results):
                self.ax_3d.text(xs[i], ys[i], zs[i], '  ' + r['prn'], 
                               color='black', fontsize=8, weight='bold',
                               bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.6))
            
            # 更新标题
            self.ax_3d.set_title(f'GPS卫星3D空间分布 ({len(self.batch_results)}颗)\n可拖动旋转视角', 
                                fontsize=12, weight='bold', color='darkblue', pad=10, fontproperties='Microsoft YaHei')
            
            # 设置坐标轴范围
            max_sat_range = max(max(abs(min(xs)), abs(max(xs))),
                               max(abs(min(ys)), abs(max(ys))),
                               max(abs(min(zs)), abs(max(zs))))
            axis_limit = max(max_sat_range * 1.1, 6371 * 1.5)
            self.ax_3d.set_xlim([-axis_limit, axis_limit])
            self.ax_3d.set_ylim([-axis_limit, axis_limit])
            self.ax_3d.set_zlim([-axis_limit, axis_limit])
            
            # 更新状态栏
            if hasattr(self, 'status_3d'):
                self.status_3d.config(text=f'已显示 {len(self.batch_results)} 颗卫星 | 可使用鼠标旋转、缩放视图')
        
        # 设置坐标轴
        self.ax_3d.set_xlabel('X (km)', fontsize=9, weight='bold', color='navy', fontproperties='Microsoft YaHei')
        self.ax_3d.set_ylabel('Y (km)', fontsize=9, weight='bold', color='navy', fontproperties='Microsoft YaHei')
        self.ax_3d.set_zlabel('Z (km)', fontsize=9, weight='bold', color='navy', fontproperties='Microsoft YaHei')
        self.ax_3d.grid(True, linestyle=':', alpha=0.3, linewidth=0.5)
        self.ax_3d.set_box_aspect([1,1,1])
        self.ax_3d.tick_params(colors='black', labelsize=7)
        
        # 刷新画布
        if self.canvas_3d:
            self.canvas_3d.draw()

    def _get_absolute_path(self, path: str) -> str:
        """将相对路径或绝对路径转换为绝对路径"""
        if not path:
            return ''
        if os.path.isabs(path):
            return path
        # 相对路径：先尝试相对于nav目录，再尝试相对于根目录
        nav_path = os.path.join(self.nav_dir, path)
        if os.path.exists(nav_path):
            return nav_path
        root_path = os.path.join(self.root_dir, path)
        if os.path.exists(root_path):
            return root_path
        return path  # 如果都不存在，返回原路径（可能用户输入了其他路径）

    def _get_relative_path(self, path: str) -> str:
        """将绝对路径转换为相对路径（相对于根目录）"""
        if not path:
            return ''
        try:
            return os.path.relpath(path, self.root_dir)
        except ValueError:
            return path  # 如果无法转换，返回原路径

    def _update_default_hints(self):
        """更新默认值提示标签的显示状态"""
        accent = getattr(self, 'accent', 'blue')
        muted = getattr(self, 'text_muted', 'gray')
        # 检查文件是否为默认文件（使用相对路径比较）
        current_file = self.file_path.get()
        default_rel_path = self._get_relative_path(self.default_file)
        is_default_file = (os.path.exists(self.default_file) and 
                          current_file and 
                          current_file == default_rel_path)
        
        if is_default_file:
            self.lbl_default_file.config(text='默认文件', foreground=accent)
            self.lbl_manual_hint.config(text='如需使用其他文件，请点击右侧按钮手动添加', foreground=muted)
        else:
            self.lbl_default_file.config(text='自定义文件', foreground=accent)
            self.lbl_manual_hint.config(text='已切换为自定义导航文件', foreground=muted)
        
        # 检查时间是否为默认时间
        current_time = self.obs_time.get()
        is_default_time = current_time == self.default_time
        
        if is_default_time:
            self.lbl_default_time.config(text='默认时间', foreground=accent)
        else:
            self.lbl_default_time.config(text='自定义时间', foreground=accent)

    def choose_file(self):
        path = filedialog.askopenfilename(
            title='选择RINEX导航文件',
            filetypes=[
                ('GPS导航文件 (*.22n)', '*.22n'),
                ('GPS导航文件 (*.n)', '*.n'),
                ('GPS导航文件 (*.N)', '*.N'),
                ('GLONASS导航文件 (*.g)', '*.g'),
                ('GLONASS导航文件 (*.G)', '*.G'),
                ('所有文件', '*.*')
            ],
            defaultextension='.22n',
            initialdir=self.nav_dir  # 默认打开nav目录
        )
        if path:
            # 转换为相对路径显示
            rel_path = self._get_relative_path(path)
            self.file_path.set(rel_path)

    def _on_file_changed(self, *args):
        """当文件路径改变时，更新默认文件提示的显示状态"""
        self._update_default_hints()

    def _on_time_changed(self, *args):
        """当观测时间改变时，更新默认时间提示的显示状态"""
        self._update_default_hints()

    def auto_load_default(self):
        """
        自动加载默认文件（静默加载，不显示消息框）
        """
        file_path = self._get_absolute_path(self.file_path.get())
        if file_path and os.path.exists(file_path):
            try:
                lines = read_file(file_path)
            except Exception:
                return  # 如果加载失败，静默失败，用户可以手动点击解析
            if not lines:
                return
            header, body = split_header_body(lines)
            if not body:
                return
            # 检查文件类型
            file_type = 'UNKNOWN'
            for ln in header:
                if 'GLONASS' in ln.upper():
                    file_type = 'GLONASS'
                    break
                elif 'GPS' in ln.upper() or 'NAV DATA' in ln.upper():
                    file_type = 'GPS'
                    break
            fname = self.file_path.get().lower()
            if file_type == 'UNKNOWN':
                if fname.endswith('.g'):
                    file_type = 'GLONASS'
                elif fname.endswith('.n') or fname.endswith('.22n'):
                    file_type = 'GPS'
            if file_type == 'GLONASS':
                return  # GLONASS文件不自动加载
            self.leap_seconds = get_leap_seconds(header)
            self.ephs = extract_gps_ephemeris(body)
            if self.ephs:
                svs = sorted({e['prn'] for e in self.ephs})
                self.cbo_sv['values'] = svs
                if svs:
                    self.cbo_sv.set(svs[0])

    def load_nav(self):
        if not self.file_path.get():
            messagebox.showwarning('提示', '请先选择导航文件。')
            return
        file_path = self._get_absolute_path(self.file_path.get())
        if not os.path.exists(file_path):
            messagebox.showerror('错误', f'文件不存在：{file_path}\n请确保文件已放在nav文件夹中。')
            return
        try:
            lines = read_file(file_path)
        except Exception as ex:
            messagebox.showerror('错误', f'无法读取文件：{ex}')
            return
        if not lines:
            messagebox.showerror('错误', '文件为空。')
            return
        header, body = split_header_body(lines)
        if not body:
            messagebox.showerror('错误', '文件中没有星历数据。')
            return
        # Check file type from header
        file_type = 'UNKNOWN'
        for ln in header:
            if 'GLONASS' in ln.upper():
                file_type = 'GLONASS'
                break
            elif 'GPS' in ln.upper() or 'NAV DATA' in ln.upper():
                file_type = 'GPS'
                break
        # Also check filename extension
        fname = self.file_path.get().lower()
        if file_type == 'UNKNOWN':
            if fname.endswith('.g'):
                file_type = 'GLONASS'
            elif fname.endswith('.n') or fname.endswith('.22n'):
                file_type = 'GPS'
        if file_type == 'GLONASS':
            messagebox.showwarning('提示', '当前文件是GLONASS格式（.g），本程序目前仅支持GPS格式（.n 或 .22n）。\n请选择GPS广播星历文件（brdc*.n 或 *.22n）。')
            self.cbo_sv['values'] = []
            return
        self.leap_seconds = get_leap_seconds(header)
        self.ephs = extract_gps_ephemeris(body)
        if not self.ephs:
            messagebox.showwarning('提示', '未在文件中找到GPS星历记录。\n请确认文件是RINEX 2格式的GPS导航文件（.n 或 .22n）。')
            self.cbo_sv['values'] = []
            return
        svs = sorted({e['prn'] for e in self.ephs})
        self.cbo_sv['values'] = svs
        self.cbo_sv.set(svs[0])
        messagebox.showinfo('完成', f'解析到 {len(self.ephs)} 条GPS星历；闰秒={self.leap_seconds}')

    def fill_params(self, eph: dict):
        self.tree.delete(*self.tree.get_children())
        show_keys = ['af0','af1','af2','IODE','Crs','DeltaN','M0','Cuc','e','Cus','sqrtA','Toe','Cic','Omega0','Cis','i0','Crc','omega','OmegaDot','IDOT']
        for k in show_keys:
            self.tree.insert('', 'end', values=(k, f"{eph[k]:.12e}" if isinstance(eph[k], float) else str(eph[k])))

    def calculate(self):
        if not self.ephs:
            messagebox.showwarning('提示', '请先解析星历。')
            return
        sv = self.cbo_sv.get()
        if not sv:
            messagebox.showwarning('提示', '请选择一个卫星。')
            return
        try:
            # <-- 【公式中的t来源】观测时间t从GUI界面的"观测时间(UTC)"输入框获取
            # 用户输入的格式: YYYY-MM-DD HH:MM:SS (UTC时间)
            # 例如: "2023-09-10 00:00:00"
            t = datetime.strptime(self.obs_time.get(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except Exception:
            messagebox.showerror('错误', '观测时间格式应为 YYYY-MM-DD HH:MM:SS')
            return
        # pick the record with Toe closest to observation time within same file
        # <-- 【t的转换】将UTC时间t转换为GPS周内秒(sow)，用于后续计算 tk = t - toe
        _, sow = utc_to_gps_seconds_of_week(t, self.leap_seconds)
        cand = [e for e in self.ephs if e['prn'] == sv]
        if not cand:
            messagebox.showerror('错误', f'未找到 {sv} 的星历记录')
            return
        e = min(cand, key=lambda x: abs((sow - x['Toe'] + 302400) % 604800 - 302400))
        self.fill_params(e)
        X, Y, Z, _ = compute_gps_ecef(e, t, self.leap_seconds)
        # 使用Treeview显示坐标（包含m和km两列）
        self.tree_xyz.delete(*self.tree_xyz.get_children())
        self.tree_xyz.insert('', 'end', values=('X', f'{X:,.3f}', f'{X/1000:,.6f}'))
        self.tree_xyz.insert('', 'end', values=('Y', f'{Y:,.3f}', f'{Y/1000:,.6f}'))
        self.tree_xyz.insert('', 'end', values=('Z', f'{Z:,.3f}', f'{Z/1000:,.6f}'))
        
        # 计算并显示卫星与地心的距离
        distance = math.sqrt(X**2 + Y**2 + Z**2)
        self.tree_distance.delete(*self.tree_distance.get_children())
        self.tree_distance.insert('', 'end', values=('D', f'{distance:,.3f}', f'{distance/1000:,.6f}'))
        
        # 更新滚动区域，确保新内容可见
        self._update_scroll_region()

    def calculate_all(self):
        """批量计算所有卫星的坐标"""
        if not self.ephs:
            messagebox.showwarning('提示', '请先解析星历。')
            return
        try:
            t = datetime.strptime(self.obs_time.get(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except Exception:
            messagebox.showerror('错误', '观测时间格式应为 YYYY-MM-DD HH:MM:SS')
            return
        
        _, sow = utc_to_gps_seconds_of_week(t, self.leap_seconds)
        svs = sorted({e['prn'] for e in self.ephs})
        
        self.batch_results = []
        for sv in svs:
            cand = [e for e in self.ephs if e['prn'] == sv]
            if not cand:
                continue
            e = min(cand, key=lambda x: abs((sow - x['Toe'] + 302400) % 604800 - 302400))
            X, Y, Z, params = compute_gps_ecef(e, t, self.leap_seconds)
            distance = math.sqrt(X**2 + Y**2 + Z**2)
            self.batch_results.append({
                'prn': sv, 'X': X, 'Y': Y, 'Z': Z, 'distance': distance,
                'time': t.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # 更新3D视图
        self.update_3d_view()
        
        # 在新窗口显示批量结果
        self._show_batch_results()
        messagebox.showinfo('完成', f'成功计算了 {len(self.batch_results)} 颗卫星的坐标\n3D视图已自动更新')

    def _show_batch_results(self):
        """在新窗口显示批量计算结果"""
        win = tk.Toplevel(self)
        win.title('批量计算结果')
        win.configure(bg=self.base_bg)
        win.geometry('1000x600')
        
        frame = ttk.Frame(win, style='TechCard.TFrame', padding=(self.section_pad, self.section_pad))
        frame.pack(fill='both', expand=True, padx=self.section_pad, pady=self.section_pad)
        
        ttk.Label(frame, text='所有卫星坐标 (ECEF)', style='TechSection.TLabel').pack(pady=(0, self.row_gap))
        
        tree = ttk.Treeview(frame, columns=('prn','X','Y','Z','dist'), show='headings', height=20, style='Tech.Treeview')
        tree.heading('prn', text='卫星号')
        tree.heading('X', text='X (km)')
        tree.heading('Y', text='Y (km)')
        tree.heading('Z', text='Z (km)')
        tree.heading('dist', text='距地心 (km)')
        tree.column('prn', width=80, anchor='center')
        tree.column('X', width=150, anchor='center')
        tree.column('Y', width=150, anchor='center')
        tree.column('Z', width=150, anchor='center')
        tree.column('dist', width=150, anchor='center')
        
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=tree.yview, style='Tech.Vertical.TScrollbar')
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        for res in self.batch_results:
            tree.insert('', 'end', values=(
                res['prn'],
                f"{res['X']/1000:,.6f}",
                f"{res['Y']/1000:,.6f}",
                f"{res['Z']/1000:,.6f}",
                f"{res['distance']/1000:,.6f}"
            ))

    def export_results(self):
        """导出计算结果到CSV文件"""
        if not self.batch_results:
            messagebox.showwarning('提示', '请先进行批量计算，再导出结果。')
            return
        
        file_path = filedialog.asksaveasfilename(
            title='导出结果',
            defaultextension='.csv',
            filetypes=[('CSV文件', '*.csv'), ('文本文件', '*.txt')]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['卫星号', '观测时间(UTC)', 'X(m)', 'Y(m)', 'Z(m)', 'X(km)', 'Y(km)', 'Z(km)', '距地心(m)', '距地心(km)'])
                for res in self.batch_results:
                    writer.writerow([
                        res['prn'], res['time'],
                        f"{res['X']:.3f}", f"{res['Y']:.3f}", f"{res['Z']:.3f}",
                        f"{res['X']/1000:.6f}", f"{res['Y']/1000:.6f}", f"{res['Z']/1000:.6f}",
                        f"{res['distance']:.3f}", f"{res['distance']/1000:.6f}"
                    ])
            messagebox.showinfo('成功', f'结果已导出到：\n{file_path}')
        except Exception as ex:
            messagebox.showerror('错误', f'导出失败：{ex}')

    def predict_trajectory(self):
        """预测卫星轨迹"""
        if not self.ephs:
            messagebox.showwarning('提示', '请先解析星历。')
            return
        sv = self.cbo_sv.get()
        if not sv:
            messagebox.showwarning('提示', '请选择一个卫星。')
            return
        
        # 创建对话框获取时间范围
        dialog = tk.Toplevel(self)
        dialog.title('轨迹预测参数设置')
        dialog.configure(bg=self.card_bg)
        dialog.geometry('500x300')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, style='TechCard.TFrame', padding=(20, 20))
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text='起始时间 (UTC)', style='Tech.TLabel').grid(row=0, column=0, sticky='e', padx=10, pady=10)
        start_time = ttk.Entry(frame, width=25, style='TechInput.TEntry')
        start_time.insert(0, self.obs_time.get())
        start_time.grid(row=0, column=1, sticky='w', padx=10, pady=10)
        
        ttk.Label(frame, text='时长 (分钟)', style='Tech.TLabel').grid(row=1, column=0, sticky='e', padx=10, pady=10)
        duration = ttk.Entry(frame, width=25, style='TechInput.TEntry')
        duration.insert(0, '60')
        duration.grid(row=1, column=1, sticky='w', padx=10, pady=10)
        
        ttk.Label(frame, text='时间间隔 (秒)', style='Tech.TLabel').grid(row=2, column=0, sticky='e', padx=10, pady=10)
        interval = ttk.Entry(frame, width=25, style='TechInput.TEntry')
        interval.insert(0, '60')
        interval.grid(row=2, column=1, sticky='w', padx=10, pady=10)
        
        result_data = {'positions': None}
        
        def compute():
            try:
                t_start = datetime.strptime(start_time.get(), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                dur_min = int(duration.get())
                intv_sec = int(interval.get())
            except Exception:
                messagebox.showerror('错误', '参数格式错误')
                return
            
            _, sow = utc_to_gps_seconds_of_week(t_start, self.leap_seconds)
            cand = [e for e in self.ephs if e['prn'] == sv]
            if not cand:
                messagebox.showerror('错误', f'未找到 {sv} 的星历记录')
                return
            e = min(cand, key=lambda x: abs((sow - x['Toe'] + 302400) % 604800 - 302400))
            
            positions = []
            num_points = (dur_min * 60) // intv_sec + 1
            for i in range(num_points):
                t = t_start + timedelta(seconds=i * intv_sec)
                X, Y, Z, _ = compute_gps_ecef(e, t, self.leap_seconds)
                positions.append({
                    'time': t.strftime('%Y-%m-%d %H:%M:%S'),
                    'X': X, 'Y': Y, 'Z': Z,
                    'distance': math.sqrt(X**2 + Y**2 + Z**2)
                })
            
            result_data['positions'] = positions
            dialog.destroy()
            self._show_trajectory_results(sv, positions)
        
        btn_frame = ttk.Frame(frame, style='TechCard.TFrame')
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text='计算', command=compute, style='TechAccent.TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text='取消', command=dialog.destroy, style='TechGhost.TButton').pack(side='left', padx=5)

    def _show_trajectory_results(self, sv, positions):
        """显示轨迹预测结果"""
        win = tk.Toplevel(self)
        win.title(f'{sv} 轨迹预测结果')
        win.configure(bg=self.base_bg)
        win.geometry('1000x600')
        
        frame = ttk.Frame(win, style='TechCard.TFrame', padding=(self.section_pad, self.section_pad))
        frame.pack(fill='both', expand=True, padx=self.section_pad, pady=self.section_pad)
        
        ttk.Label(frame, text=f'{sv} 轨迹数据点', style='TechSection.TLabel').pack(pady=(0, self.row_gap))
        
        tree = ttk.Treeview(frame, columns=('time','X','Y','Z','dist'), show='headings', height=20, style='Tech.Treeview')
        tree.heading('time', text='时间 (UTC)')
        tree.heading('X', text='X (km)')
        tree.heading('Y', text='Y (km)')
        tree.heading('Z', text='Z (km)')
        tree.heading('dist', text='距地心 (km)')
        tree.column('time', width=150, anchor='center')
        tree.column('X', width=150, anchor='center')
        tree.column('Y', width=150, anchor='center')
        tree.column('Z', width=150, anchor='center')
        tree.column('dist', width=150, anchor='center')
        
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=tree.yview, style='Tech.Vertical.TScrollbar')
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        for pos in positions:
            tree.insert('', 'end', values=(
                pos['time'],
                f"{pos['X']/1000:,.6f}",
                f"{pos['Y']/1000:,.6f}",
                f"{pos['Z']/1000:,.6f}",
                f"{pos['distance']/1000:,.6f}"
            ))
        
        # 添加导出按钮
        def export_traj():
            file_path = filedialog.asksaveasfilename(
                title='导出轨迹数据',
                defaultextension='.csv',
                filetypes=[('CSV文件', '*.csv')]
            )
            if file_path:
                try:
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['时间(UTC)', 'X(m)', 'Y(m)', 'Z(m)', 'X(km)', 'Y(km)', 'Z(km)', '距地心(km)'])
                        for pos in positions:
                            writer.writerow([
                                pos['time'],
                                f"{pos['X']:.3f}", f"{pos['Y']:.3f}", f"{pos['Z']:.3f}",
                                f"{pos['X']/1000:.6f}", f"{pos['Y']/1000:.6f}", f"{pos['Z']/1000:.6f}",
                                f"{pos['distance']/1000:.6f}"
                            ])
                    messagebox.showinfo('成功', f'轨迹数据已导出到：\n{file_path}')
                except Exception as ex:
                    messagebox.showerror('错误', f'导出失败：{ex}')
        
        btn_frame = ttk.Frame(frame, style='TechCard.TFrame')
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text='导出轨迹数据', command=export_traj, style='TechAccent.TButton').pack(side='left', padx=5)
        
        # 添加3D可视化按钮
        def visualize_traj():
            self._visualize_trajectory_3d(sv, positions)
        
        ttk.Button(btn_frame, text='3D可视化轨迹', command=visualize_traj, style='TechAccent.TButton').pack(side='left', padx=5)

    def _visualize_trajectory_3d(self, sv, positions):
        """3D可视化卫星轨迹"""
        if not HAS_MATPLOTLIB:
            messagebox.showwarning('提示', '需要安装matplotlib库才能使用可视化功能。\n请运行: pip install matplotlib')
            return
        
        if not positions or len(positions) < 2:
            messagebox.showwarning('提示', '轨迹数据点不足，无法进行可视化。')
            return
        
        win = tk.Toplevel(self)
        win.title(f'{sv} 轨迹3D可视化')
        win.configure(bg=self.base_bg)
        win.geometry('1200x900')
        
        # 创建带工具栏的Figure
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        import numpy as np
        
        fig = Figure(figsize=(12, 9), facecolor='white', dpi=100)
        ax = fig.add_subplot(111, projection='3d', facecolor='white')
        
        # 绘制地球
        u = np.linspace(0, 2 * np.pi, 80)
        v = np.linspace(0, np.pi, 40)
        earth_radius = 6371  # 地球半径(公里)
        x_earth = earth_radius * np.outer(np.cos(u), np.sin(v))
        y_earth = earth_radius * np.outer(np.sin(u), np.sin(v))
        z_earth = earth_radius * np.outer(np.ones(np.size(u)), np.cos(v))
        
        ax.plot_surface(x_earth, y_earth, z_earth, color='#1e90ff', alpha=0.3, 
                       edgecolor='#4169e1', linewidth=0.1, antialiased=True)
        
        # 绘制赤道和子午线
        theta = np.linspace(0, 2 * np.pi, 100)
        ax.plot(earth_radius * np.cos(theta), earth_radius * np.sin(theta), 0, 
               color='#00ff00', linewidth=1.5, alpha=0.6, label='赤道')
        ax.plot(earth_radius * np.cos(theta), 0, earth_radius * np.sin(theta), 
               color='#ff6600', linewidth=1.5, alpha=0.6, label='本初子午线')
        
        # 提取轨迹数据
        x_traj = np.array([pos['X']/1000 for pos in positions])  # 转换为km
        y_traj = np.array([pos['Y']/1000 for pos in positions])
        z_traj = np.array([pos['Z']/1000 for pos in positions])
        
        # 绘制轨迹线 - 使用渐变色
        n_points = len(positions)
        for i in range(n_points - 1):
            # 颜色从红色渐变到黄色（表示时间进展）
            color = plt.cm.hot(i / n_points)
            ax.plot(x_traj[i:i+2], y_traj[i:i+2], z_traj[i:i+2], 
                   color=color, linewidth=2.5, alpha=0.8)
        
        # 标记起点和终点
        ax.scatter([x_traj[0]], [y_traj[0]], [z_traj[0]], 
                  color='lime', s=200, marker='o', edgecolors='darkgreen', 
                  linewidths=2, label=f'起点 ({positions[0]["time"]})', zorder=5)
        ax.scatter([x_traj[-1]], [y_traj[-1]], [z_traj[-1]], 
                  color='red', s=200, marker='s', edgecolors='darkred', 
                  linewidths=2, label=f'终点 ({positions[-1]["time"]})', zorder=5)
        
        # 每隔几个点标记时间
        step = max(1, len(positions) // 10)  # 最多显示10个时间标记
        for i in range(0, len(positions), step):
            if i > 0 and i < len(positions) - 1:  # 跳过起点和终点
                ax.scatter([x_traj[i]], [y_traj[i]], [z_traj[i]], 
                          color='orange', s=100, marker='*', alpha=0.7, zorder=4)
        
        # 设置标题和标签（使用中文字体）
        ax.set_title(f'{sv} 卫星轨迹预测\n时间跨度: {positions[0]["time"]} 至 {positions[-1]["time"]}\n数据点: {len(positions)}个', 
                    fontsize=14, fontweight='bold', pad=20, fontproperties='Microsoft YaHei')
        ax.set_xlabel('X 坐标 (km)', fontsize=11, labelpad=10, fontproperties='Microsoft YaHei')
        ax.set_ylabel('Y 坐标 (km)', fontsize=11, labelpad=10, fontproperties='Microsoft YaHei')
        ax.set_zlabel('Z 坐标 (km)', fontsize=11, labelpad=10, fontproperties='Microsoft YaHei')
        
        # 设置坐标轴范围一致
        max_range = 30000  # km
        ax.set_xlim([-max_range, max_range])
        ax.set_ylim([-max_range, max_range])
        ax.set_zlim([-max_range, max_range])
        
        # 设置视角
        ax.view_init(elev=25, azim=45)
        
        # 添加图例
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9, prop={'family': 'Microsoft YaHei'})
        
        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.3)
        
        fig.tight_layout()
        
        # 嵌入Tkinter
        canvas = FigureCanvasTkAgg(fig, win)
        canvas.draw()
        
        # 添加工具栏
        toolbar = NavigationToolbar2Tk(canvas, win)
        toolbar.update()
        
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # 添加说明标签
        info_frame = ttk.Frame(win, style='TechCard.TFrame')
        info_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(info_frame, 
                 text='💡 提示: 拖动鼠标旋转视图 | 滚轮缩放 | 工具栏可保存图片 | 轨迹颜色从深红到黄色表示时间流逝', 
                 style='Tech.TLabel', foreground='#00e0ff').pack()
    
    def visualize_3d(self):
        """3D可视化卫星位置"""
        if not HAS_MATPLOTLIB:
            messagebox.showwarning('提示', '需要安装matplotlib库才能使用可视化功能。\n请运行: pip install matplotlib')
            return
        
        if not self.batch_results:
            messagebox.showwarning('提示', '请先进行批量计算，再进行可视化。')
            return
        
        win = tk.Toplevel(self)
        win.title('卫星3D可视化')
        win.configure(bg=self.base_bg)
        win.geometry('1100x800')
        
        # 创建带工具栏的Figure
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        import numpy as np
        
        fig = Figure(figsize=(11, 8), facecolor='white', dpi=100)
        ax = fig.add_subplot(111, projection='3d', facecolor='white')
        
        # 绘制地球 - 使用更高分辨率和渐变色
        u = np.linspace(0, 2 * np.pi, 100)
        v = np.linspace(0, np.pi, 50)
        earth_radius = 6371  # 地球半径(公里)
        x_earth = earth_radius * np.outer(np.cos(u), np.sin(v))
        y_earth = earth_radius * np.outer(np.sin(u), np.sin(v))
        z_earth = earth_radius * np.outer(np.ones(np.size(u)), np.cos(v))
        
        # 使用蓝色渐变绘制地球，增加透明度
        ax.plot_surface(x_earth, y_earth, z_earth, color='#1e90ff', alpha=0.4, 
                       edgecolor='#4169e1', linewidth=0.1, antialiased=True)
        
        # 绘制赤道和子午线作为参考
        theta = np.linspace(0, 2 * np.pi, 100)
        # 赤道
        eq_x = earth_radius * np.cos(theta)
        eq_y = earth_radius * np.sin(theta)
        eq_z = np.zeros_like(theta)
        ax.plot(eq_x, eq_y, eq_z, color='#00ff00', linewidth=2, alpha=0.6, label='赤道')
        
        # 本初子午线
        phi = np.linspace(0, 2 * np.pi, 100)
        pm_x = earth_radius * np.cos(phi)
        pm_y = np.zeros_like(phi)
        pm_z = earth_radius * np.sin(phi)
        ax.plot(pm_x, pm_y, pm_z, color='#ff0000', linewidth=2, alpha=0.6, label='本初子午线')
        
        # 绘制卫星 - 使用更大更醒目的标记
        xs = [r['X']/1000 for r in self.batch_results]
        ys = [r['Y']/1000 for r in self.batch_results]
        zs = [r['Z']/1000 for r in self.batch_results]
        
        # 主卫星点
        scatter = ax.scatter(xs, ys, zs, c='#ff6b00', s=200, marker='*', 
                           edgecolors='yellow', linewidths=2, alpha=0.9, 
                           label='GPS卫星', depthshade=True)
        
        # 添加从地心到卫星的连线
        for i, r in enumerate(self.batch_results):
            ax.plot([0, xs[i]], [0, ys[i]], [0, zs[i]], 
                   color='cyan', linestyle='--', linewidth=0.5, alpha=0.3)
        
        # 添加卫星标签 - 使用更大字体和背景框
        for i, r in enumerate(self.batch_results):
            ax.text(xs[i], ys[i], zs[i], '  ' + r['prn'], 
                   color='black', fontsize=11, weight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        # 标记地心
        ax.scatter([0], [0], [0], c='red', s=300, marker='o', 
                  edgecolors='darkred', linewidths=2, label='地心')
        
        # 设置坐标轴
        ax.set_xlabel('X (km)', fontsize=12, weight='bold', color='navy')
        ax.set_ylabel('Y (km)', fontsize=12, weight='bold', color='navy')
        ax.set_zlabel('Z (km)', fontsize=12, weight='bold', color='navy')
        ax.set_title('GPS卫星3D空间分布图\n(可拖动旋转、滚轮缩放)', 
                    fontsize=16, weight='bold', color='darkblue', pad=20)
        
        # 设置网格
        ax.grid(True, linestyle=':', alpha=0.3, linewidth=0.5)
        
        # 设置坐标轴范围 - 确保地球和卫星都可见
        max_sat_range = max(max(abs(min(xs)), abs(max(xs))),
                           max(abs(min(ys)), abs(max(ys))),
                           max(abs(min(zs)), abs(max(zs))))
        axis_limit = max(max_sat_range * 1.1, earth_radius * 1.5)
        ax.set_xlim([-axis_limit, axis_limit])
        ax.set_ylim([-axis_limit, axis_limit])
        ax.set_zlim([-axis_limit, axis_limit])
        
        # 设置相等的坐标轴比例
        ax.set_box_aspect([1,1,1])
        
        # 设置初始视角
        ax.view_init(elev=20, azim=45)
        
        # 添加图例
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
        
        # 设置刻度标签颜色
        ax.tick_params(colors='black', labelsize=9)
        
        # 调整布局
        fig.tight_layout()
        
        # 创建画布和工具栏
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        
        # 添加matplotlib工具栏
        toolbar_frame = ttk.Frame(win, style='TechCard.TFrame')
        toolbar_frame.pack(side='top', fill='x')
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        
        canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # 添加说明文字
        info_frame = ttk.Frame(win, style='TechCard.TFrame', padding=(10, 5))
        info_frame.pack(side='bottom', fill='x')
        ttk.Label(info_frame, 
                 text=f'共显示 {len(self.batch_results)} 颗卫星 | 可使用鼠标左键旋转、右键平移、滚轮缩放 | 工具栏可保存图片',
                 style='TechHint.TLabel').pack()


if __name__ == '__main__':
    App().mainloop()


