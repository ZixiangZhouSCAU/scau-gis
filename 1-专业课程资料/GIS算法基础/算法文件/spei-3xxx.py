import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import norm
import matplotlib.pyplot as plt

# --------------------------
# 1. 定义SPEI计算所需核心函数
# --------------------------

def thornthwaite_pet(temp, lat, month):
    """
    用桑斯威特法计算月潜在蒸散量（PET）
    参数：
        temp: 月均温（℃）
        lat: 纬度（度）
        month: 月份（1-12）
    返回：
        pet: 潜在蒸散量（mm）
    """
    # 计算热指数i（仅当温度≥0℃时有效）
    i = np.where(temp >= 0, (temp / 5) ** 1.514, 0)
    # 计算年热指数I（全年12个月i的总和）
    I = np.sum(i)
    
    # 计算a系数（与I相关的经验系数）
    a = (6.75e-7) * (I ** 3) - (7.71e-5) * (I ** 2) + (1.792e-2) * I + 0.49239
    
    # 计算每月可照时数修正系数（基于纬度和月份）
    # 太阳赤纬（弧度）
    delta = 0.409 * np.sin((2 * np.pi / 12) * month - 1.39)
    lat_rad = np.radians(lat)  # 纬度转弧度
    # 日出时角（弧度）
    omega = np.arccos(-np.tan(lat_rad) * np.tan(delta))
    # 每月可照时数（小时）
    N = (24 / np.pi) * omega
    # 修正系数（标准化为12小时基准）
    K = N / 12
    
    # 计算PET（mm/月）
    pet = K * 16 * ((10 * temp / I) ** a) if I != 0 else 0
    return pet


def spei_standardize(cum_d):
    """
    对累积水分盈亏量进行标准化（简单Z-score标准化）
    参数：
        cum_d: 3个月滚动累积水分盈亏量（需排除NaN）
    返回：
        spei: 标准化后的SPEI值
    """
    cum_d = np.array(cum_d)
    
    if len(cum_d) == 0:
        return np.array([])
    
    # 简单的Z-score标准化：(x - mean) / std
    mean_val = np.mean(cum_d)
    std_val = np.std(cum_d, ddof=1)  # 使用样本标准差
    
    if std_val == 0 or np.isnan(std_val):
        # 如果标准差为0，返回全0
        return np.zeros_like(cum_d)
    
    spei = (cum_d - mean_val) / std_val
    
    return spei




# --------------------------
# 2. 主流程：读取数据并计算SPEI-3
# --------------------------

def calculate_spei3(data_path):
    """
    读取数据并计算SPEI-3
    参数：
        data_path: 数据文件路径（CSV格式，需包含列：month, precip, temp, lat）
    返回：
        result: 包含SPEI-3的DataFrame
    """
    # 读取数据
    df = pd.read_csv(data_path)
    # 确保月份按顺序排列
    df = df.sort_values('month').reset_index(drop=True)
    
    # 1. 计算每月PET
    df['pet'] = df.apply(
        lambda row: thornthwaite_pet(row['temp'], row['lat'], row['month']), 
        axis=1
    )
    
    # 2. 计算水分盈亏量D = 降水量 - PET
    df['d'] = df['precip'] - df['pet']
    
    # 3. 计算3个月滚动累积水分盈亏量（从第3个月开始有效）
    df['cum_d_3'] = df['d'].rolling(window=3, min_periods=3).sum()
    
    # 4. 对累积值进行标准化，得到SPEI-3
    # 提取有效累积值（排除前2个月的NaN）
    valid_cum_d = df['cum_d_3'].dropna().values
    if len(valid_cum_d) == 0:
        df['spei3'] = np.nan
        return df
    
    # 标准化
    spei_values = spei_standardize(valid_cum_d)
    # 填充回DataFrame（前2个月为NaN）
    df.loc[df['cum_d_3'].notna(), 'spei3'] = spei_values
    
    return df


def calculate_spei3_from_df(df):
    """
    从DataFrame直接计算SPEI-3（不读取文件）
    参数：
        df: 包含列：month, precip, temp, lat的DataFrame
    返回：
        result: 包含SPEI-3的DataFrame
    """
    df = df.copy()
    # 确保月份按顺序排列
    df = df.sort_values('month').reset_index(drop=True)
    
    # 1. 计算每月PET
    df['pet'] = df.apply(
        lambda row: thornthwaite_pet(row['temp'], row['lat'], row['month']), 
        axis=1
    )
    
    # 2. 计算水分盈亏量D = 降水量 - PET
    df['d'] = df['precip'] - df['pet']
    
    # 3. 计算3个月滚动累积水分盈亏量（从第3个月开始有效）
    df['cum_d_3'] = df['d'].rolling(window=3, min_periods=3).sum()
    
    # 4. 对累积值进行标准化，得到SPEI-3
    # 提取有效累积值（排除前2个月的NaN）
    valid_cum_d = df['cum_d_3'].dropna().values
    if len(valid_cum_d) == 0:
        df['spei3'] = np.nan
        return df
    
    # 标准化
    spei_values = spei_standardize(valid_cum_d)
    # 填充回DataFrame（前2个月为NaN）
    df.loc[df['cum_d_3'].notna(), 'spei3'] = spei_values
    
    return df


# --------------------------
# 3. 主程序：读取实际数据并计算
# --------------------------
if __name__ == "__main__":
    # 读取Excel数据
    data_path = r"D:\桌面\data\Stations_normalized-sorted_按时间排序.xlsx"
    print("正在读取数据...")
    df = pd.read_excel(data_path)
    print(f"数据加载完成！共 {len(df)} 条记录，{df['station_id'].nunique()} 个站点")
    
    # 为每个站点单独计算SPEI-3
    result_list = []
    stations = df['station_id'].unique()
    
    print(f"\n开始计算各站点SPEI-3...")
    for i, station_id in enumerate(stations, 1):
        # 提取单个站点数据
        station_df = df[df['station_id'] == station_id].copy()
        station_df = station_df.sort_values(['year', 'month']).reset_index(drop=True)
        
        # 重命名列以匹配calculate_spei3函数的要求
        station_df['lat'] = station_df['latitude']
        
        # 计算SPEI-3（使用原有的calculate_spei3函数）
        station_result = calculate_spei3_from_df(station_df)
        
        # 将计算结果保存到newSPEI3列
        station_result['newSPEI3'] = station_result['spei3']
        
        # 保留原始数据的所有列
        for col in df.columns:
            if col not in station_result.columns:
                station_result[col] = station_df[col].values
        
        result_list.append(station_result)
        print(f"  [{i}/{len(stations)}] 站点 {station_id} 完成")
    
    # 合并所有站点结果
    final_df = pd.concat(result_list, ignore_index=True)
    
    # 保存结果（使用新文件名）
    output_path = r"D:\桌面\data\Stations_with_corrected_SPEI3.xlsx"
    print(f"\n正在保存结果到 {output_path}...")
    final_df.to_excel(output_path, index=False)
    print("保存完成！")
    
    # 显示统计信息
    print("\n" + "="*60)
    print("SPEI-3 计算结果统计：")
    print(f"  有效记录数: {final_df['newSPEI3'].notna().sum()} / {len(final_df)}")
    print(f"  newSPEI3 范围: [{final_df['newSPEI3'].min():.3f}, {final_df['newSPEI3'].max():.3f}]")
    print(f"  newSPEI3 均值: {final_df['newSPEI3'].mean():.3f}")
    print(f"  newSPEI3 标准差: {final_df['newSPEI3'].std():.3f}")
    print("="*60)
    
    # 显示前10行对比
    print("\n前10行数据（对比原SPEI-3和newSPEI3）：")
    print(final_df[['station_id', 'year', 'month', 'SPEI-3', 'newSPEI3']].head(10))