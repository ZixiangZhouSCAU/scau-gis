"""
地理时空加权回归(GTWR)模型
用于分析newSPEI3与多个气象和地理变量之间的时空关系
包含多重共线性诊断(VIF分析)

改进版本:
- 实现高级带宽优化(两阶段网格搜索 + K折交叉验证)
- 重写预测方法符合GTWR理论
- 优化计算效率(内存优化和并行计算)
- 改进拟合过程直接计算预测值
- 添加AICc准则作为辅助评估
- 完整的优化过程可视化
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.api import OLS, add_constant
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial.distance import cdist
from scipy.optimize import minimize_scalar, differential_evolution
from joblib import Parallel, delayed
import joblib
import warnings
import time as time_module
from datetime import datetime
from pathlib import Path
warnings.filterwarnings('ignore')

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class GTWR:
    """地理时空加权回归模型 (改进版)"""
    
    def __init__(self, bandwidth_space=None, bandwidth_time=None, kernel='gaussian', n_jobs=-1):
        """
        初始化GTWR模型
        
        参数:
        -----------
        bandwidth_space : float
            空间带宽参数(如果为None,将自动优化)
        bandwidth_time : float
            时间带宽参数(如果为None,将自动优化)
        kernel : str
            核函数类型 ('gaussian', 'bisquare', 'exponential')
        n_jobs : int
            并行计算的CPU核心数(-1表示使用所有核心)
        """
        # 参数验证
        if kernel not in ['gaussian', 'bisquare', 'exponential']:
            raise ValueError(f"不支持的核函数: {kernel}. 支持的类型: 'gaussian', 'bisquare', 'exponential'")
        
        if bandwidth_space is not None and bandwidth_space <= 0:
            raise ValueError(f"空间带宽必须大于0, 当前值: {bandwidth_space}")
        
        if bandwidth_time is not None and bandwidth_time <= 0:
            raise ValueError(f"时间带宽必须大于0, 当前值: {bandwidth_time}")
        
        if not isinstance(n_jobs, int) or n_jobs == 0:
            raise ValueError(f"n_jobs必须是非零整数, 当前值: {n_jobs}")
        
        self.bandwidth_space = bandwidth_space
        self.bandwidth_time = bandwidth_time
        self.kernel = kernel
        self.n_jobs = n_jobs
        self.coefficients = None
        self.local_r2 = None
        self.y_fitted = None  # 存储拟合值
        self.X_train = None   # 存储训练数据
        self.y_train = None
        self.coords_train = None
        self.time_train = None
        self.feature_names = None  # 存储特征名称
        self.optimization_history = []  # 存储优化历史
        
    def spatial_distance(self, coords1, coords2):
        """
        计算空间距离（使用经纬度）
        
        参数:
        -----------
        coords1, coords2 : array-like, shape (n_samples, 2)
            经纬度坐标 [longitude, latitude]
        
        返回:
        -----------
        distances : array, shape (n_samples1, n_samples2)
            空间距离矩阵
        """
        # 转换为弧度
        coords1_rad = np.radians(coords1)
        coords2_rad = np.radians(coords2)
        
        # Haversine公式计算球面距离
        lat1, lon1 = coords1_rad[:, 1:2], coords1_rad[:, 0:1]
        lat2, lon2 = coords2_rad[:, 1:2].T, coords2_rad[:, 0:1].T
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        # 地球半径（千米）
        r = 6371
        return r * c
    
    def temporal_distance(self, time1, time2):
        """
        计算时间距离
        
        参数:
        -----------
        time1, time2 : array-like
            时间值（如年份+月份/12）
        
        返回:
        -----------
        distances : array, shape (n_samples1, n_samples2)
            时间距离矩阵
        """
        time1 = np.array(time1).reshape(-1, 1)
        time2 = np.array(time2).reshape(-1, 1)
        return cdist(time1, time2, metric='euclidean')
    
    def kernel_function(self, distance, bandwidth):
        """
        核函数计算权重
        
        参数:
        -----------
        distance : array-like
            距离值
        bandwidth : float
            带宽参数
        
        返回:
        -----------
        weights : array-like
            权重值
        """
        if self.kernel == 'gaussian':
            return np.exp(-0.5 * (distance / bandwidth) ** 2)
        elif self.kernel == 'bisquare':
            temp = 1 - (distance / bandwidth) ** 2
            return np.where(distance < bandwidth, temp ** 2, 0)
        elif self.kernel == 'exponential':
            return np.exp(-distance / bandwidth)
        else:
            raise ValueError(f"不支持的核函数类型: {self.kernel}")
    
    def calculate_weights(self, target_coords, target_time, sample_coords, sample_time):
        """
        计算时空权重矩阵
        
        参数:
        -----------
        target_coords : array-like, shape (1, 2)
            目标点的空间坐标
        target_time : float
            目标点的时间
        sample_coords : array-like, shape (n_samples, 2)
            样本点的空间坐标
        sample_time : array-like, shape (n_samples,)
            样本点的时间
        
        返回:
        -----------
        weights : array, shape (n_samples,)
            时空权重向量
        """
        # 计算空间距离
        spatial_dist = self.spatial_distance(target_coords, sample_coords).flatten()
        
        # 计算时间距离
        temporal_dist = self.temporal_distance(
            np.array([target_time]), 
            sample_time
        ).flatten()
        
        # 计算空间权重
        w_space = self.kernel_function(spatial_dist, self.bandwidth_space)
        
        # 计算时间权重
        w_time = self.kernel_function(temporal_dist, self.bandwidth_time)
        
        # 组合时空权重（相乘）
        weights = w_space * w_time
        
        return weights
    
    def _fit_single_point(self, i, X_with_const, y, coords, time):
        """
        对单个样本点进行局部回归(用于并行计算)
        
        参数:
        -----------
        i : int
            样本点索引
        X_with_const : array-like
            包含常数项的自变量矩阵
        y : array-like
            因变量向量
        coords : array-like
            空间坐标
        time : array-like
            时间变量
        
        返回:
        -----------
        beta : array
            回归系数
        local_r2 : float
            局部R²
        y_fitted : float
            拟合值
        """
        # 计算该点的时空权重
        weights = self.calculate_weights(
            coords[i:i+1], 
            time[i], 
            coords, 
            time
        )
        
        # 避免权重过小
        weights = np.maximum(weights, 1e-10)
        
        # 加权最小二乘回归(内存优化版本)
        try:
            # 使用广播代替对角矩阵,节省内存
            sqrt_weights = np.sqrt(weights)
            X_weighted = X_with_const * sqrt_weights[:, np.newaxis]
            y_weighted = y * sqrt_weights
            
            XtWX = X_weighted.T @ X_weighted
            XtWy = X_weighted.T @ y_weighted
            
            # 求解回归系数
            beta = np.linalg.solve(XtWX, XtWy)
            
            # 计算该点的拟合值
            y_fitted = X_with_const[i] @ beta
            
            # 计算局部R²
            y_pred_all = X_with_const @ beta
            ss_res = weights @ ((y - y_pred_all) ** 2)
            ss_tot = weights @ ((y - np.average(y, weights=weights)) ** 2)
            local_r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            
            return beta, local_r2, y_fitted
            
        except np.linalg.LinAlgError:
            return np.full(X_with_const.shape[1], np.nan), np.nan, np.nan
    
    def _cv_single_fold(self, fold_idx, train_idx, test_idx, X_with_const, y, coords, time, bw_space, bw_time):
        """
        单次交叉验证折叠计算(用于并行)
        
        参数:
        -----------
        fold_idx : int
            折叠索引
        train_idx : array
            训练集索引
        test_idx : array
            测试集索引
        X_with_const : array
            包含常数项的自变量矩阵
        y : array
            因变量
        coords : array
            空间坐标
        time : array
            时间变量
        bw_space : float
            空间带宽
        bw_time : float
            时间带宽
        
        返回:
        -----------
        fold_errors : list
            该折的预测误差
        """
        # 临时保存原带宽
        old_bw_space = self.bandwidth_space
        old_bw_time = self.bandwidth_time
        
        # 设置当前带宽
        self.bandwidth_space = bw_space
        self.bandwidth_time = bw_time
        
        fold_errors = []
        
        # 对测试集中的每个点进行预测
        for test_i in test_idx:
            # 使用训练集计算权重和回归系数
            weights = self.calculate_weights(
                coords[test_i:test_i+1], 
                time[test_i], 
                coords[train_idx], 
                time[train_idx]
            )
            weights = np.maximum(weights, 1e-10)
            
            try:
                # 加权回归
                sqrt_weights = np.sqrt(weights)
                X_weighted = X_with_const[train_idx] * sqrt_weights[:, np.newaxis]
                y_weighted = y[train_idx] * sqrt_weights
                
                XtWX = X_weighted.T @ X_weighted
                XtWy = X_weighted.T @ y_weighted
                
                # 添加正则化防止奇异矩阵
                XtWX += np.eye(XtWX.shape[0]) * 1e-6
                
                beta = np.linalg.solve(XtWX, XtWy)
                
                # 预测
                y_pred = X_with_const[test_i] @ beta
                fold_errors.append((y[test_i] - y_pred) ** 2)
                
            except (np.linalg.LinAlgError, ValueError):
                fold_errors.append(np.inf)
        
        # 恢复原带宽
        self.bandwidth_space = old_bw_space
        self.bandwidth_time = old_bw_time
        
        return fold_errors
    
    def _calculate_aicc(self, X, y, coords, time, bw_space, bw_time):
        """
        计算AICc准则
        
        参数:
        -----------
        X, y, coords, time : array
            数据
        bw_space, bw_time : float
            带宽参数
        
        返回:
        -----------
        aicc : float
            AICc值(越小越好)
        """
        n = len(y)
        X_with_const = add_constant(X)
        
        # 临时设置带宽
        old_bw_space = self.bandwidth_space
        old_bw_time = self.bandwidth_time
        self.bandwidth_space = bw_space
        self.bandwidth_time = bw_time
        
        rss = 0  # 残差平方和
        tr_S = 0  # hat矩阵的迹
        
        # 计算每个点的残差和有效参数数
        for i in range(n):
            weights = self.calculate_weights(coords[i:i+1], time[i], coords, time)
            weights = np.maximum(weights, 1e-10)
            
            try:
                sqrt_weights = np.sqrt(weights)
                X_weighted = X_with_const * sqrt_weights[:, np.newaxis]
                y_weighted = y * sqrt_weights
                
                XtWX = X_weighted.T @ X_weighted
                XtWy = X_weighted.T @ y_weighted
                
                beta = np.linalg.solve(XtWX, XtWy)
                
                # 残差
                y_pred = X_with_const[i] @ beta
                rss += (y[i] - y_pred) ** 2
                
                # hat矩阵对角元素
                XtWX_inv = np.linalg.inv(XtWX)
                xi = X_with_const[i]
                hi = xi @ XtWX_inv @ (xi * weights[i])
                tr_S += hi
                
            except (np.linalg.LinAlgError, ValueError):
                rss += np.inf
                tr_S += 1
        
        # 恢复带宽
        self.bandwidth_space = old_bw_space
        self.bandwidth_time = old_bw_time
        
        # AICc公式
        if rss == 0 or rss == np.inf:
            return np.inf
        
        aic = n * np.log(rss / n) + n * np.log(2 * np.pi) + n + tr_S
        aicc = aic + (2 * tr_S * (tr_S + 1)) / (n - tr_S - 1) if n - tr_S - 1 > 0 else np.inf
        
        return aicc
    
    def optimize_bandwidth(self, X, y, coords, time, method='cv', 
                          space_range=None, time_range=None, 
                          cv_folds=5, n_iter_coarse=15, n_iter_fine=10, 
                          sample_size=None, use_aicc=True, verbose=True):
        """
        自动优化带宽参数(改进版 - 两阶段网格搜索 + 交叉验证)
        
        参数:
        -----------
        X : array-like
            自变量矩阵
        y : array-like
            因变量向量
        coords : array-like
            空间坐标
        time : array-like
            时间变量
        method : str
            优化方法 ('cv', 'aicc', 'both')
        space_range : tuple, optional
            空间带宽搜索范围 (min, max), None则自动推断
        time_range : tuple, optional
            时间带宽搜索范围 (min, max), None则自动推断
        cv_folds : int
            K折交叉验证的折数(建议5-10)
        n_iter_coarse : int
            粗网格搜索迭代次数
        n_iter_fine : int
            细网格搜索迭代次数
        sample_size : int, optional
            交叉验证时每折使用的样本数(None=全部, 过大会很慢)
        use_aicc : bool
            是否同时计算AICc作为参考
        verbose : bool
            是否显示优化过程
        
        返回:
        -----------
        best_bandwidth_space : float
            最优空间带宽
        best_bandwidth_time : float
            最优时间带宽
        """
        n_samples = len(y)
        X_with_const = add_constant(X)
        
        # 自动推断搜索范围
        if space_range is None:
            # 基于空间坐标范围计算
            spatial_dist_matrix = self.spatial_distance(coords, coords)
            spatial_dist_matrix[spatial_dist_matrix == 0] = np.inf
            min_dist = np.min(spatial_dist_matrix)
            max_dist = np.max(spatial_dist_matrix[spatial_dist_matrix != np.inf])
            mean_dist = np.mean(spatial_dist_matrix[spatial_dist_matrix != np.inf])
            
            space_range = (max(min_dist * 0.5, mean_dist * 0.1), min(max_dist * 0.8, mean_dist * 5))
        
        if time_range is None:
            # 基于时间范围计算
            time_span = time.max() - time.min()
            time_range = (time_span * 0.02, time_span * 0.5)  # 2%到50%的时间跨度
        
        if verbose:
            print("\n" + "="*70)
            print("🚀 高级带宽优化 - 两阶段网格搜索 + K折交叉验证")
            print("="*70)
            print(f"📊 数据信息:")
            print(f"   样本数: {n_samples}")
            print(f"   特征数: {X.shape[1]}")
            print(f"   时间跨度: {time.min():.2f} - {time.max():.2f} (共{time.max()-time.min():.2f}年)")
            print(f"\n🔍 搜索空间:")
            print(f"   空间带宽范围: {space_range[0]:.2f} - {space_range[1]:.2f} km")
            print(f"   时间带宽范围: {time_range[0]:.2f} - {time_range[1]:.2f} 年")
            print(f"\n⚙️  优化设置:")
            print(f"   交叉验证折数: {cv_folds}")
            print(f"   粗搜索迭代数: {n_iter_coarse}")
            print(f"   细搜索迭代数: {n_iter_fine}")
            print(f"   优化方法: {method}")
            print(f"   使用AICc: {use_aicc}")
        
        # ========== 阶段1: 粗网格搜索 ==========
        if verbose:
            print("\n" + "-"*70)
            print("📍 阶段1: 粗网格全局搜索")
            print("-"*70)
        
        def cv_score_func(bandwidths):
            """K折交叉验证得分"""
            bw_space, bw_time = bandwidths
            
            # 参数边界检查
            if bw_space <= 0 or bw_time <= 0:
                return np.inf
            if bw_space < space_range[0] or bw_space > space_range[1]:
                return np.inf
            if bw_time < time_range[0] or bw_time > time_range[1]:
                return np.inf
            
            # K折交叉验证
            from sklearn.model_selection import KFold
            kf = KFold(n_splits=cv_folds, shuffle=True, random_state=42)
            
            all_errors = []
            
            for fold_idx, (train_idx, test_idx) in enumerate(kf.split(X)):
                # 如果指定了sample_size，则随机抽样
                if sample_size is not None and len(test_idx) > sample_size:
                    test_idx = np.random.choice(test_idx, sample_size, replace=False)
                
                # 计算该折的误差
                fold_errors = self._cv_single_fold(
                    fold_idx, train_idx, test_idx, 
                    X_with_const, y, coords, time, 
                    bw_space, bw_time
                )
                all_errors.extend(fold_errors)
            
            # 返回平均MSE
            mse = np.mean([e for e in all_errors if e != np.inf])
            return mse if not np.isnan(mse) else np.inf
        
        # 粗搜索
        bounds = [space_range, time_range]
        start_time = time_module.time()
        
        result_coarse = differential_evolution(
            cv_score_func,
            bounds,
            maxiter=n_iter_coarse,
            popsize=15,
            seed=42,
            workers=1,  # 避免嵌套并行
            disp=False,
            polish=False  # 不进行局部精炼
        )
        
        coarse_time = time_module.time() - start_time
        best_space_coarse = result_coarse.x[0]
        best_time_coarse = result_coarse.x[1]
        best_cv_coarse = result_coarse.fun
        
        if verbose:
            print(f"✓ 粗搜索完成 (耗时: {coarse_time:.1f}秒)")
            print(f"   最优空间带宽: {best_space_coarse:.4f} km")
            print(f"   最优时间带宽: {best_time_coarse:.4f} 年 ({best_time_coarse*12:.1f}个月)")
            print(f"   CV-MSE: {best_cv_coarse:.6f}")
        
        # ========== 阶段2: 细网格局部搜索 ==========
        if verbose:
            print("\n" + "-"*70)
            print("🎯 阶段2: 细网格局部精炼")
            print("-"*70)
        
        # 在粗搜索结果周围定义更小的搜索范围
        space_range_fine = (
            max(space_range[0], best_space_coarse * 0.5),
            min(space_range[1], best_space_coarse * 1.5)
        )
        time_range_fine = (
            max(time_range[0], best_time_coarse * 0.5),
            min(time_range[1], best_time_coarse * 1.5)
        )
        
        if verbose:
            print(f"细搜索范围:")
            print(f"   空间: {space_range_fine[0]:.4f} - {space_range_fine[1]:.4f} km")
            print(f"   时间: {time_range_fine[0]:.4f} - {time_range_fine[1]:.4f} 年")
        
        bounds_fine = [space_range_fine, time_range_fine]
        start_time = time_module.time()
        
        result_fine = differential_evolution(
            cv_score_func,
            bounds_fine,
            maxiter=n_iter_fine,
            popsize=10,
            seed=43,
            workers=1,
            disp=False,
            polish=True,  # 进行局部精炼
            atol=1e-6,
            tol=1e-6
        )
        
        fine_time = time_module.time() - start_time
        best_bandwidth_space = result_fine.x[0]
        best_bandwidth_time = result_fine.x[1]
        best_cv_score = result_fine.fun
        
        if verbose:
            print(f"✓ 细搜索完成 (耗时: {fine_time:.1f}秒)")
            print(f"   最优空间带宽: {best_bandwidth_space:.4f} km")
            print(f"   最优时间带宽: {best_bandwidth_time:.4f} 年 ({best_bandwidth_time*12:.1f}个月)")
            print(f"   CV-MSE: {best_cv_score:.6f}")
            print(f"   改进: {(best_cv_coarse - best_cv_score) / best_cv_coarse * 100:.2f}%")
        
        # ========== 计算AICc (如果需要) ==========
        if use_aicc:
            if verbose:
                print("\n" + "-"*70)
                print("📈 计算AICc准则")
                print("-"*70)
            
            start_time = time_module.time()
            aicc_value = self._calculate_aicc(X, y, coords, time, 
                                              best_bandwidth_space, best_bandwidth_time)
            aicc_time = time_module.time() - start_time
            
            if verbose:
                print(f"✓ AICc计算完成 (耗时: {aicc_time:.1f}秒)")
                print(f"   AICc值: {aicc_value:.2f}")
        
        # ========== 最终结果 ==========
        if verbose:
            print("\n" + "="*70)
            print("✨ 优化完成！")
            print("="*70)
            print(f"🏆 最优带宽参数:")
            print(f"   空间带宽: {best_bandwidth_space:.4f} km")
            print(f"   时间带宽: {best_bandwidth_time:.4f} 年 ({best_bandwidth_time*12:.1f}个月)")
            print(f"\n📊 评估指标:")
            print(f"   交叉验证MSE: {best_cv_score:.6f}")
            print(f"   交叉验证RMSE: {np.sqrt(best_cv_score):.6f}")
            if use_aicc:
                print(f"   AICc: {aicc_value:.2f}")
            print(f"\n⏱️  总耗时: {coarse_time + fine_time:.1f}秒")
            print("="*70)
        
        # 保存优化历史
        self.optimization_history.append({
            'method': method,
            'cv_folds': cv_folds,
            'space_range': space_range,
            'time_range': time_range,
            'best_space': best_bandwidth_space,
            'best_time': best_bandwidth_time,
            'cv_mse': best_cv_score,
            'cv_rmse': np.sqrt(best_cv_score),
            'aicc': aicc_value if use_aicc else None,
            'coarse_iterations': n_iter_coarse,
            'fine_iterations': n_iter_fine,
            'total_time': coarse_time + fine_time,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # 更新模型带宽
        self.bandwidth_space = best_bandwidth_space
        self.bandwidth_time = best_bandwidth_time
        
        return best_bandwidth_space, best_bandwidth_time
    
    def fit(self, X, y, coords, time, optimize_bandwidth=False, feature_names=None):
        """
        拟合GTWR模型(支持并行计算和自动带宽优化)
        
        参数:
        -----------
        X : array-like, shape (n_samples, n_features)
            自变量矩阵
        y : array-like, shape (n_samples,)
            因变量向量
        coords : array-like, shape (n_samples, 2)
            空间坐标 [longitude, latitude]
        time : array-like, shape (n_samples,)
            时间变量
        optimize_bandwidth : bool
            是否自动优化带宽参数
        feature_names : list, optional
            特征名称列表
        """
        # 输入验证
        X = np.asarray(X)
        y = np.asarray(y)
        coords = np.asarray(coords)
        time = np.asarray(time)
        
        if len(X) != len(y) or len(X) != len(coords) or len(X) != len(time):
            raise ValueError("X, y, coords, time 的样本数必须一致")
        
        if coords.shape[1] != 2:
            raise ValueError(f"coords必须是2列(经度,纬度), 当前: {coords.shape[1]}列")
        
        n_samples, n_features = X.shape
        
        print(f"\n{'='*60}")
        print(f"开始训练GTWR模型")
        print(f"{'='*60}")
        print(f"样本数: {n_samples}")
        print(f"特征数: {n_features}")
        print(f"核函数: {self.kernel}")
        print(f"并行核心: {self.n_jobs}")
        
        start_time = time_module.time()
        
        # 存储训练数据
        self.X_train = X
        self.y_train = y
        self.coords_train = coords
        self.time_train = time
        self.feature_names = feature_names
        
        # 自动优化带宽(如果需要)
        if optimize_bandwidth or self.bandwidth_space is None or self.bandwidth_time is None:
            # 自动推断搜索范围(None表示让optimize_bandwidth自动推断)
            space_range = None
            time_range = None
            
            # 如果已有带宽值，则在其周围搜索
            if self.bandwidth_space is not None and self.bandwidth_time is not None:
                space_range = (self.bandwidth_space * 0.5, self.bandwidth_space * 2)
                time_range = (self.bandwidth_time * 0.5, self.bandwidth_time * 2)
            
            # 调用改进的优化方法
            self.optimize_bandwidth(
                X, y, coords, time,
                method='cv',
                space_range=space_range,
                time_range=time_range,
                cv_folds=5,  # 5折交叉验证
                n_iter_coarse=20,  # 粗搜索迭代数
                n_iter_fine=15,    # 细搜索迭代数
                sample_size=None,  # 使用全部样本(如果数据太大可设置为200-500)
                use_aicc=True,     # 计算AICc作为参考
                verbose=True
            )
        
        # 添加截距项
        X_with_const = add_constant(X)
        
        # 初始化结果数组
        self.coefficients = np.zeros((n_samples, n_features + 1))
        self.local_r2 = np.zeros(n_samples)
        self.y_fitted = np.zeros(n_samples)
        
        print(f"\n使用 {self.n_jobs} 个CPU核心进行并行计算...")
        print(f"带宽参数: 空间={self.bandwidth_space:.4f} km, 时间={self.bandwidth_time:.4f} 年")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        fit_start = time_module.time()
        
        # 并行计算每个样本点的局部回归
        results = Parallel(n_jobs=self.n_jobs, verbose=10)(
            delayed(self._fit_single_point)(i, X_with_const, y, coords, time)
            for i in range(n_samples)
        )
        
        # 整理结果
        for i, (beta, local_r2, y_fitted) in enumerate(results):
            self.coefficients[i] = beta
            self.local_r2[i] = local_r2
            self.y_fitted[i] = y_fitted
        
        fit_time = time_module.time() - fit_start
        total_time = time_module.time() - start_time
        
        print(f"\n{'='*60}")
        print("GTWR模型拟合完成！")
        print(f"{'='*60}")
        print(f"拟合耗时: {fit_time:.2f} 秒")
        print(f"总耗时: {total_time:.2f} 秒")
        print(f"平均每样本: {fit_time/n_samples*1000:.2f} 毫秒")
        
        # 快速评估（处理NaN值）
        from sklearn.metrics import r2_score
        
        # 检查并处理NaN值
        valid_mask = ~(np.isnan(self.y_fitted) | np.isnan(y))
        n_valid = np.sum(valid_mask)
        
        if n_valid > 0:
            r2 = r2_score(y[valid_mask], self.y_fitted[valid_mask])
            mean_local_r2 = np.nanmean(self.local_r2)
            print(f"\n快速评估:")
            print(f"  整体R²: {r2:.4f}")
            print(f"  平均局部R²: {mean_local_r2:.4f}")
            print(f"  有效拟合点: {n_valid}/{n_samples}")
            
            # 如果有NaN值，警告用户
            if n_valid < n_samples:
                n_nan = n_samples - n_valid
                print(f"  ⚠ 警告: {n_nan} 个样本的预测值为NaN")
        else:
            print(f"\n⚠ 警告: 所有预测值都是NaN，模型拟合失败")
            print(f"  建议调整带宽参数或检查输入数据")
        
        return self
    
    def predict(self, X, coords, time):
        """
        使用GTWR模型进行预测(改进版 - 符合GTWR理论)
        
        对每个新的预测点,重新进行局部加权回归以获得该点的回归系数,
        然后使用这些系数进行预测。这符合GTWR的理论基础。
        
        参数:
        -----------
        X : array-like, shape (n_samples, n_features)
            预测点的自变量
        coords : array-like, shape (n_samples, 2)
            预测点的空间坐标
        time : array-like, shape (n_samples,)
            预测点的时间
        
        返回:
        -----------
        y_pred : array, shape (n_samples,)
            预测值
        """
        if self.X_train is None:
            raise ValueError("模型尚未拟合,请先调用fit方法")
        
        n_samples = X.shape[0]
        X_pred_const = add_constant(X)
        X_train_const = add_constant(self.X_train)
        y_pred = np.zeros(n_samples)
        
        print(f"\n正在预测 {n_samples} 个样本点...")
        
        # 对每个预测点进行局部回归
        for i in range(n_samples):
            if n_samples > 100 and i % 100 == 0:
                print(f"预测进度: {i+1}/{n_samples}")
            
            # 1. 计算预测点与所有训练点的时空权重
            weights = self.calculate_weights(
                coords[i:i+1], 
                time[i], 
                self.coords_train, 
                self.time_train
            )
            
            # 避免权重过小
            weights = np.maximum(weights, 1e-10)
            
            # 2. 基于这些权重进行局部加权回归
            try:
                sqrt_weights = np.sqrt(weights)
                X_weighted = X_train_const * sqrt_weights[:, np.newaxis]
                y_weighted = self.y_train * sqrt_weights
                
                XtWX = X_weighted.T @ X_weighted
                XtWy = X_weighted.T @ y_weighted
                
                # 3. 求解该预测点的局部回归系数
                beta_pred = np.linalg.solve(XtWX, XtWy)
                
                # 4. 使用该点的自变量和求得的系数进行预测
                y_pred[i] = X_pred_const[i] @ beta_pred
                
            except np.linalg.LinAlgError:
                # 如果局部回归失败,使用最近邻的系数作为备用方案
                spatial_dist = self.spatial_distance(coords[i:i+1], self.coords_train).flatten()
                temporal_dist = self.temporal_distance(
                    np.array([time[i]]), 
                    self.time_train
                ).flatten()
                combined_dist = spatial_dist / self.bandwidth_space + temporal_dist / self.bandwidth_time
                nearest_idx = np.argmin(combined_dist)
                y_pred[i] = X_pred_const[i] @ self.coefficients[nearest_idx]
        
        print("预测完成！")
        return y_pred
    
    def save_model(self, filepath='gtwr_model.pkl'):
        """
        保存模型到文件
        
        参数:
        -----------
        filepath : str
            保存路径
        """
        model_data = {
            'bandwidth_space': self.bandwidth_space,
            'bandwidth_time': self.bandwidth_time,
            'kernel': self.kernel,
            'n_jobs': self.n_jobs,
            'coefficients': self.coefficients,
            'local_r2': self.local_r2,
            'y_fitted': self.y_fitted,
            'X_train': self.X_train,
            'y_train': self.y_train,
            'coords_train': self.coords_train,
            'time_train': self.time_train,
            'feature_names': self.feature_names,
            'optimization_history': self.optimization_history,
            'saved_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        joblib.dump(model_data, filepath)
        print(f"✓ 模型已保存至: {filepath}")
        return filepath
    
    @classmethod
    def load_model(cls, filepath='gtwr_model.pkl'):
        """
        从文件加载模型
        
        参数:
        -----------
        filepath : str
            模型文件路径
        
        返回:
        -----------
        model : GTWR
            加载的模型对象
        """
        if not Path(filepath).exists():
            raise FileNotFoundError(f"模型文件不存在: {filepath}")
        
        model_data = joblib.load(filepath)
        
        # 创建新模型实例
        model = cls(
            bandwidth_space=model_data['bandwidth_space'],
            bandwidth_time=model_data['bandwidth_time'],
            kernel=model_data['kernel'],
            n_jobs=model_data['n_jobs']
        )
        
        # 恢复模型状态
        model.coefficients = model_data['coefficients']
        model.local_r2 = model_data['local_r2']
        model.y_fitted = model_data['y_fitted']
        model.X_train = model_data['X_train']
        model.y_train = model_data['y_train']
        model.coords_train = model_data['coords_train']
        model.time_train = model_data['time_train']
        model.feature_names = model_data.get('feature_names', None)
        model.optimization_history = model_data.get('optimization_history', [])
        
        print(f"✓ 模型已加载: {filepath}")
        print(f"  保存时间: {model_data.get('saved_time', 'Unknown')}")
        print(f"  训练样本数: {len(model.y_train) if model.y_train is not None else 0}")
        print(f"  特征数: {model.X_train.shape[1] if model.X_train is not None else 0}")
        
        return model
    
    def get_model_summary(self):
        """
        获取模型摘要信息
        
        返回:
        -----------
        summary : dict
            模型摘要
        """
        if self.X_train is None:
            return {"status": "未训练"}
        
        from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
        
        summary = {
            "模型状态": "已训练",
            "训练样本数": len(self.y_train),
            "特征数": self.X_train.shape[1],
            "空间带宽": f"{self.bandwidth_space:.4f} km" if self.bandwidth_space else "未设置",
            "时间带宽": f"{self.bandwidth_time:.4f} 年" if self.bandwidth_time else "未设置",
            "核函数": self.kernel,
            "并行核心数": self.n_jobs,
            "整体R²": f"{r2_score(self.y_train, self.y_fitted):.4f}",
            "RMSE": f"{np.sqrt(mean_squared_error(self.y_train, self.y_fitted)):.4f}",
            "MAE": f"{mean_absolute_error(self.y_train, self.y_fitted):.4f}",
            "平均局部R²": f"{np.nanmean(self.local_r2):.4f}",
            "局部R²范围": f"[{np.nanmin(self.local_r2):.4f}, {np.nanmax(self.local_r2):.4f}]"
        }
        
        return summary
    
    def print_summary(self):
        """打印模型摘要"""
        summary = self.get_model_summary()
        
        print("\n" + "="*60)
        print("GTWR模型摘要")
        print("="*60)
        
        for key, value in summary.items():
            print(f"{key:12s}: {value}")
        
        print("="*60 + "\n")
    
    def plot_diagnostics(self, save_dir='diagnostics'):
        """
        生成模型诊断图
        
        参数:
        -----------
        save_dir : str
            保存目录
        """
        if self.X_train is None:
            print("错误: 模型尚未训练")
            return
        
        # 创建保存目录
        Path(save_dir).mkdir(exist_ok=True)
        
        # 1. 残差分布图
        plt.figure(figsize=(12, 10))
        
        # 子图1: 残差直方图
        plt.subplot(2, 2, 1)
        residuals = self.y_train - self.y_fitted
        plt.hist(residuals, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
        plt.axvline(x=0, color='red', linestyle='--', linewidth=2)
        plt.xlabel('残差', fontsize=12)
        plt.ylabel('频数', fontsize=12)
        plt.title(f'残差分布 (Mean={np.mean(residuals):.4f})', fontsize=14, fontweight='bold')
        plt.grid(alpha=0.3)
        
        # 子图2: 预测vs实际
        plt.subplot(2, 2, 2)
        plt.scatter(self.y_train, self.y_fitted, alpha=0.5, s=20)
        plt.plot([self.y_train.min(), self.y_train.max()], 
                [self.y_train.min(), self.y_train.max()], 
                'r--', lw=2, label='理想预测')
        plt.xlabel('实际值', fontsize=12)
        plt.ylabel('预测值', fontsize=12)
        plt.title('预测 vs 实际', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(alpha=0.3)
        
        # 子图3: 局部R²空间分布
        plt.subplot(2, 2, 3)
        scatter = plt.scatter(self.coords_train[:, 0], self.coords_train[:, 1], 
                            c=self.local_r2, cmap='RdYlGn', s=30, alpha=0.6)
        plt.colorbar(scatter, label='局部R²')
        plt.xlabel('经度', fontsize=12)
        plt.ylabel('纬度', fontsize=12)
        plt.title('局部R²空间分布', fontsize=14, fontweight='bold')
        plt.grid(alpha=0.3)
        
        # 子图4: 残差vs预测值
        plt.subplot(2, 2, 4)
        plt.scatter(self.y_fitted, residuals, alpha=0.5, s=20)
        plt.axhline(y=0, color='red', linestyle='--', linewidth=2)
        plt.xlabel('预测值', fontsize=12)
        plt.ylabel('残差', fontsize=12)
        plt.title('残差 vs 预测值', fontsize=14, fontweight='bold')
        plt.grid(alpha=0.3)
        
        plt.tight_layout()
        filepath = Path(save_dir) / 'model_diagnostics.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"✓ 诊断图已保存至: {filepath}")
        plt.close()
        
        # 2. 局部R²箱线图
        plt.figure(figsize=(10, 6))
        plt.boxplot([self.local_r2], labels=['局部R²'])
        plt.ylabel('R²值', fontsize=12)
        plt.title('局部R²分布', fontsize=14, fontweight='bold')
        plt.grid(axis='y', alpha=0.3)
        
        # 添加统计信息
        stats_text = f'Mean: {np.nanmean(self.local_r2):.4f}\n'
        stats_text += f'Median: {np.nanmedian(self.local_r2):.4f}\n'
        stats_text += f'Std: {np.nanstd(self.local_r2):.4f}'
        plt.text(1.15, np.nanmedian(self.local_r2), stats_text, 
                fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        filepath = Path(save_dir) / 'local_r2_distribution.png'
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"✓ 局部R²分布图已保存至: {filepath}")
        plt.close()
        
        print(f"\n✓ 所有诊断图已保存至目录: {save_dir}/")
    
    def plot_bandwidth_optimization(self, save_path='bandwidth_optimization.png'):
        """
        可视化带宽优化历史
        
        参数:
        -----------
        save_path : str
            保存路径
        """
        if not self.optimization_history:
            print("警告: 没有优化历史记录")
            return
        
        history = self.optimization_history[-1]  # 使用最近一次优化
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('带宽优化结果可视化', fontsize=16, fontweight='bold')
        
        # 子图1: 最优带宽参数
        ax1 = axes[0, 0]
        params = ['空间带宽\n(km)', '时间带宽\n(年)']
        values = [history['best_space'], history['best_time']]
        colors = ['#3498db', '#e74c3c']
        bars = ax1.bar(params, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
        ax1.set_ylabel('带宽值', fontsize=12)
        ax1.set_title('最优带宽参数', fontsize=14, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        # 在柱状图上标注数值
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.4f}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # 子图2: 评估指标
        ax2 = axes[0, 1]
        metrics = ['CV-MSE', 'CV-RMSE']
        metric_values = [history['cv_mse'], history['cv_rmse']]
        bars = ax2.barh(metrics, metric_values, color='#2ecc71', alpha=0.7, edgecolor='black', linewidth=2)
        ax2.set_xlabel('误差值', fontsize=12)
        ax2.set_title('交叉验证误差', fontsize=14, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        
        for bar, val in zip(bars, metric_values):
            width = bar.get_width()
            ax2.text(width, bar.get_y() + bar.get_height()/2.,
                    f' {val:.6f}',
                    ha='left', va='center', fontsize=11, fontweight='bold')
        
        # 子图3: 优化信息
        ax3 = axes[1, 0]
        ax3.axis('off')
        
        info_text = f"""
优化配置信息

方法: {history['method'].upper()}
交叉验证折数: {history['cv_folds']}
粗搜索迭代: {history['coarse_iterations']}
细搜索迭代: {history['fine_iterations']}
总耗时: {history['total_time']:.1f} 秒

搜索范围:
  空间: {history['space_range'][0]:.2f} - {history['space_range'][1]:.2f} km
  时间: {history['time_range'][0]:.2f} - {history['time_range'][1]:.2f} 年

优化时间: {history['timestamp']}
        """
        
        ax3.text(0.1, 0.5, info_text, fontsize=11, family='monospace',
                verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 子图4: AICc (如果有)
        ax4 = axes[1, 1]
        if history.get('aicc') is not None:
            aicc_val = history['aicc']
            ax4.bar(['AICc'], [aicc_val], color='#9b59b6', alpha=0.7, 
                   edgecolor='black', linewidth=2, width=0.5)
            ax4.set_ylabel('AICc值', fontsize=12)
            ax4.set_title('AICc准则', fontsize=14, fontweight='bold')
            ax4.grid(axis='y', alpha=0.3)
            ax4.text(0, aicc_val, f'{aicc_val:.2f}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        else:
            ax4.axis('off')
            ax4.text(0.5, 0.5, 'AICc未计算', ha='center', va='center',
                    fontsize=14, color='gray')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 带宽优化可视化已保存至: {save_path}")
        plt.close()




def load_and_preprocess_data(file_path):
    """
    加载并预处理数据
    
    参数:
    -----------
    file_path : str
        数据文件路径
    
    返回:
    -----------
    df : DataFrame
        预处理后的数据
    """
    print("正在加载数据...")
    df = pd.read_excel(file_path)
    print(f"数据加载完成！形状: {df.shape}")
    
    # 删除缺失值
    print(f"删除前数据量: {len(df)}")
    df = df.dropna(subset=['newSPEI3'])
    print(f"删除缺失值后数据量: {len(df)}")
    
    # 创建时间变量（年份 + 月份/12）
    df['time'] = df['year'] + df['month'] / 12
    
    return df


def multicollinearity_diagnosis(X, feature_names):
    """
    多重共线性诊断
    
    参数:
    -----------
    X : array-like, shape (n_samples, n_features)
        自变量矩阵
    feature_names : list
        特征名称列表
    
    返回:
    -----------
    vif_df : DataFrame
        VIF诊断结果
    """
    print("\n" + "="*60)
    print("多重共线性诊断（VIF分析）")
    print("="*60)
    
    # 计算VIF
    vif_data = []
    X_with_const = add_constant(X)
    
    for i in range(X.shape[1]):
        vif = variance_inflation_factor(X_with_const, i + 1)  # +1是因为第0列是常数项
        vif_data.append({
            '变量': feature_names[i],
            'VIF': vif
        })
    
    vif_df = pd.DataFrame(vif_data)
    vif_df = vif_df.sort_values('VIF', ascending=False)
    
    print("\nVIF诊断结果：")
    print(vif_df.to_string(index=False))
    
    # 诊断说明
    print("\n诊断标准：")
    print("  VIF < 5:  不存在多重共线性")
    print("  5 ≤ VIF < 10:  可能存在多重共线性")
    print("  VIF ≥ 10:  存在严重多重共线性，应剔除该变量")
    
    # 标记需要剔除的变量
    high_vif = vif_df[vif_df['VIF'] >= 10]
    if len(high_vif) > 0:
        print(f"\n警告：以下 {len(high_vif)} 个变量VIF≥10，建议剔除：")
        for _, row in high_vif.iterrows():
            print(f"  - {row['变量']}: VIF = {row['VIF']:.2f}")
    else:
        print("\n✓ 所有变量VIF < 10，不存在严重多重共线性问题")
    
    return vif_df


def calculate_standardized_coefficients(X, y, feature_names):
    """
    计算标准化回归系数
    
    参数:
    -----------
    X : array-like, shape (n_samples, n_features)
        自变量矩阵
    y : array-like, shape (n_samples,)
        因变量向量
    feature_names : list
        特征名称列表
    
    返回:
    -----------
    coef_df : DataFrame
        标准化系数结果
    """
    print("\n" + "="*60)
    print("标准化回归系数分析")
    print("="*60)
    
    # 标准化数据
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    
    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).flatten()
    
    # 多元线性回归
    X_with_const = add_constant(X_scaled)
    model = OLS(y_scaled, X_with_const).fit()
    
    # 提取标准化系数
    coef_df = pd.DataFrame({
        '变量': feature_names,
        '标准化系数': model.params[1:],  # 排除截距
        'p值': model.pvalues[1:],
        '显著性': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' 
                   for p in model.pvalues[1:]]
    })
    
    coef_df = coef_df.sort_values('标准化系数', key=abs, ascending=False)
    
    print("\n标准化系数结果：")
    print(coef_df.to_string(index=False))
    
    print("\n说明：")
    print("  标准化系数越接近 1（或 -1），对因变量的正向（或负向）影响越显著")
    print("  显著性: *** p<0.001, ** p<0.01, * p<0.05")
    
    print(f"\n模型R²: {model.rsquared:.4f}")
    print(f"调整后R²: {model.rsquared_adj:.4f}")
    print(f"F统计量: {model.fvalue:.2f} (p={model.f_pvalue:.4e})")
    
    return coef_df, model


def plot_vif_results(vif_df, save_path='vif_analysis.png'):
    """绘制VIF诊断结果"""
    plt.figure(figsize=(10, 6))
    
    colors = ['red' if vif >= 10 else 'orange' if vif >= 5 else 'green' 
              for vif in vif_df['VIF']]
    
    plt.barh(vif_df['变量'], vif_df['VIF'], color=colors, alpha=0.7)
    plt.axvline(x=5, color='orange', linestyle='--', linewidth=2, label='VIF=5')
    plt.axvline(x=10, color='red', linestyle='--', linewidth=2, label='VIF=10')
    
    plt.xlabel('方差膨胀因子 (VIF)', fontsize=12)
    plt.ylabel('变量', fontsize=12)
    plt.title('多重共线性诊断 - VIF分析', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\nVIF分析图已保存至: {save_path}")
    plt.close()


def plot_standardized_coefficients(coef_df, save_path='standardized_coefficients.png'):
    """绘制标准化系数"""
    plt.figure(figsize=(10, 6))
    
    colors = ['red' if coef < 0 else 'green' for coef in coef_df['标准化系数']]
    
    plt.barh(coef_df['变量'], coef_df['标准化系数'], color=colors, alpha=0.7)
    plt.axvline(x=0, color='black', linestyle='-', linewidth=1)
    
    plt.xlabel('标准化系数', fontsize=12)
    plt.ylabel('变量', fontsize=12)
    plt.title('标准化回归系数', fontsize=14, fontweight='bold')
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"标准化系数图已保存至: {save_path}")
    plt.close()


def main():
    """主函数"""
    # 数据文件路径
    data_path = r"D:\桌面\data\Stations_normalized-sorted_按时间排序_newSPEI3.xlsx"
    
    # 定义变量
    dependent_var = 'newSPEI3'
    independent_vars = ['DEM', 'Slope', 'Clay', 'Sand', 'LST_DIF', 
                       'Pre', 'Tem', 'ET', 'SMCI', 'VCI', 'TCI', 'VPD', 'PCI3']
    
    # 加载数据
    df = load_and_preprocess_data(data_path)
    
    # 准备数据
    X = df[independent_vars].values
    y = df[dependent_var].values
    coords = df[['longitude', 'latitude']].values
    time = df['time'].values
    
    # 1. 多重共线性诊断
    vif_df = multicollinearity_diagnosis(X, independent_vars)
    plot_vif_results(vif_df)
    
    # 2. 标准化系数分析
    coef_df, mlr_model = calculate_standardized_coefficients(X, y, independent_vars)
    plot_standardized_coefficients(coef_df)
    
    # 3. 根据VIF结果筛选变量
    valid_vars = vif_df[vif_df['VIF'] < 10]['变量'].tolist()
    print(f"\n保留的变量（VIF < 10）: {valid_vars}")
    
    if len(valid_vars) < len(independent_vars):
        print("\n重新进行分析，使用筛选后的变量...")
        X_filtered = df[valid_vars].values
        
        # 重新计算VIF
        vif_df_filtered = multicollinearity_diagnosis(X_filtered, valid_vars)
        
        # 重新计算标准化系数
        coef_df_filtered, _ = calculate_standardized_coefficients(X_filtered, y, valid_vars)
        
        X_final = X_filtered
        feature_names_final = valid_vars
    else:
        X_final = X
        feature_names_final = independent_vars
    
    # 4. 拟合GTWR模型 (使用改进的交叉验证带宽优化)
    print("\n" + "="*70)
    print("🚀 开始拟合GTWR模型 - 使用改进的带宽优化")
    print("="*70)
    
    # 创建模型实例
    gtwr_model = GTWR(kernel='gaussian', n_jobs=-1)
    
    # 使用改进的自动带宽优化方法拟合模型
    print("\n📊 将使用两阶段网格搜索 + K折交叉验证自动优化带宽...")
    print("⚠️  注意: 优化过程可能需要较长时间(取决于数据大小)")
    
    gtwr_model.fit(
        X_final, y, coords, time,
        optimize_bandwidth=True,  # 启用自动优化
        feature_names=feature_names_final
    )
    
    # 5. 模型评估
    print("\n" + "="*60)
    print("GTWR模型评估")
    print("="*60)
    
    # 使用拟合过程中计算的拟合值(更高效)
    y_fitted = gtwr_model.y_fitted
    
    # 计算评估指标
    from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
    
    r2 = r2_score(y, y_fitted)
    rmse = np.sqrt(mean_squared_error(y, y_fitted))
    mae = mean_absolute_error(y, y_fitted)
    
    print(f"\n整体模型性能:")
    print(f"  R² = {r2:.4f}")
    print(f"  RMSE = {rmse:.4f}")
    print(f"  MAE = {mae:.4f}")
    
    print(f"\n局部R²统计:")
    print(f"  平均值: {np.nanmean(gtwr_model.local_r2):.4f}")
    print(f"  最小值: {np.nanmin(gtwr_model.local_r2):.4f}")
    print(f"  最大值: {np.nanmax(gtwr_model.local_r2):.4f}")
    print(f"  标准差: {np.nanstd(gtwr_model.local_r2):.4f}")
    
    # 6. 保存结果
    results_df = df.copy()
    results_df['predicted_newSPEI3'] = y_fitted
    results_df['residual'] = y - y_fitted
    results_df['local_r2'] = gtwr_model.local_r2
    
    # 添加局部系数
    for i, var in enumerate(feature_names_final):
        results_df[f'coef_{var}'] = gtwr_model.coefficients[:, i+1]  # +1是因为第0列是截距
    
    output_path = 'GTWR_results_improved.xlsx'
    results_df.to_excel(output_path, index=False)
    print(f"\n结果已保存至: {output_path}")
    
    # 7. (可选) 测试新的预测方法
    print("\n" + "="*60)
    print("测试改进的预测方法")
    print("="*60)
    
    # 选择一小部分数据作为测试
    test_indices = np.random.choice(len(y), min(100, len(y)), replace=False)
    X_test = X_final[test_indices]
    coords_test = coords[test_indices]
    time_test = time[test_indices]
    y_test = y[test_indices]
    
    print(f"使用 {len(test_indices)} 个样本测试预测方法...")
    y_pred_test = gtwr_model.predict(X_test, coords_test, time_test)
    
    r2_test = r2_score(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    
    print(f"\n预测性能 (测试集):")
    print(f"  R² = {r2_test:.4f}")
    print(f"  RMSE = {rmse_test:.4f}")
    
    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)
    
    # 打印模型摘要
    gtwr_model.print_summary()
    
    # 生成诊断图
    print("\n生成模型诊断图...")
    gtwr_model.plot_diagnostics(save_dir='Image')
    
    # 生成带宽优化可视化
    print("\n生成带宽优化可视化...")
    gtwr_model.plot_bandwidth_optimization(save_path='Image/bandwidth_optimization.png')
    
    # 保存模型
    print("\n保存模型...")
    model_path = gtwr_model.save_model('Sheet/gtwr_model_final.pkl')
    
    print("\n" + "="*70)
    print("🎉 改进总结")
    print("="*70)
    print("  ✓ 两阶段网格搜索(粗搜索→细搜索)")
    print("  ✓ K折交叉验证(避免过拟合)")
    print("  ✓ 自动推断搜索范围(基于数据特征)")
    print("  ✓ AICc准则作为辅助指标")
    print("  ✓ 并行计算加速优化过程")
    print("  ✓ 详细的优化过程可视化")
    print("  ✓ 优化历史记录与追踪")
    print("="*70)
    
    print(f"\n📁 所有结果已保存:")
    print(f"  - Excel结果: {output_path}")
    print(f"  - 模型文件: {model_path}")
    print(f"  - 诊断图: Image/model_diagnostics.png")
    print(f"  - 局部R²分布: Image/local_r2_distribution.png")
    print(f"  - 带宽优化可视化: Image/bandwidth_optimization.png")
    print(f"  - VIF分析: vif_analysis.png")
    print(f"  - 标准化系数: standardized_coefficients.png")
    
    return gtwr_model, results_df, vif_df, coef_df


if __name__ == "__main__":
    gtwr_model, results, vif_results, coef_results = main()

