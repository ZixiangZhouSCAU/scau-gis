"""
GTWR + XGBoost 耦合模型

说明：
- 读取 GTWR 的输出（`GTWR_results.xlsx`）或在不存在时运行 `GTWR.py` 生成。
- 构造 XGBoost 的输入特征：
    1) GTWR 的估算值（predicted_newSPEI3）
    2) 一开始被 VIF 检验剔除的自变量
    3) 所有没有被剔除的输入 GTWR 的原始自变量
- 训练 XGBoost 回归模型预测 `newSPEI3`，保存评估结果、特征重要性和模型。

使用：
    python Models/GTWR-XGBoost.py

依赖：pandas, numpy, scikit-learn, xgboost, openpyxl, joblib
"""
import os
import sys
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import joblib
import warnings
warnings.filterwarnings('ignore')

# 设置字体：西文使用Times New Roman，中文使用宋体
from matplotlib import font_manager
plt.rcParams['font.sans-serif'] = ['Times New Roman', 'SimSun', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
# 确保中文显示
import matplotlib
matplotlib.rcParams['font.family'] = ['Times New Roman', 'SimSun']


def ensure_gtwr_results(gtwr_results_path, gtwr_script_path):
    """如果 GTWR 结果文件不存在，调用 GTWR.py 生成。"""
    if os.path.exists(gtwr_results_path):
        print(f"找到已有 GTWR 结果文件: {gtwr_results_path}")
        return True

    print(f"未找到 {gtwr_results_path}，将运行 GTWR 脚本以生成结果...")
    # 使用相同的 Python 可执行程序运行 GTWR.py
    try:
        cmd = [sys.executable, gtwr_script_path]
        proc = subprocess.run(cmd, check=True)
        print("GTWR 脚本运行完成。请检查输出文件是否已生成。")
    except subprocess.CalledProcessError as e:
        print("运行 GTWR.py 失败：", e)
        return False

    return os.path.exists(gtwr_results_path)


def build_features(results_df, independent_vars, vif_threshold=10.0):
    """根据说明构造 XGBoost 的特征集。

    包含：GTWR 的估算值 'predicted_newSPEI3'，
    GTWR 的残差 'residual'（重要特征，捕捉GTWR未解释的信息），
    被 VIF 剔除的变量（VIF>=vif_threshold），
    以及所有没有被剔除的原始自变量（VIF < vif_threshold）。
    最终特征为：所有原始自变量（无重复） + predicted_newSPEI3。
    """
    # 重新计算 VIF 简单判别（利用 pandas + statsmodels）
    from statsmodels.api import add_constant
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    X = results_df[independent_vars].values
    X_const = add_constant(X)
    vif_vals = []
    for i in range(X.shape[1]):
        try:
            vif = variance_inflation_factor(X_const, i+1)  # +1 因为第0是常数
        except Exception:
            vif = np.nan
        vif_vals.append(vif)

    vif_df = pd.DataFrame({'变量': independent_vars, 'VIF': vif_vals}).sort_values('VIF', ascending=False)
    removed_vars = vif_df[vif_df['VIF'] >= vif_threshold]['变量'].tolist()
    kept_vars = vif_df[vif_df['VIF'] < vif_threshold]['变量'].tolist()

    # 特征集合：所有原始自变量（包括被删的）+ GTWR 预测值
    features = list(dict.fromkeys(independent_vars + ['predicted_newSPEI3']))

    return features, vif_df, removed_vars, kept_vars


def plot_fitting_results(y_true, y_pred, title='XGBoost拟合效果', save_path='XGBoost_fitting.png'):
    """
    绘制拟合散点图
    
    参数:
    -----------
    y_true : array-like
        真实值
    y_pred : array-like
        预测值
    title : str
        图表标题
    save_path : str
        保存路径
    """
    # 计算评估指标
    r2 = r2_score(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    
    # 创建图形
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 左图：散点图 + 1:1线
    ax1.scatter(y_true, y_pred, alpha=0.5, s=20, edgecolors='k', linewidths=0.5)
    
    # 绘制1:1线
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    ax1.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2, label='1:1线')
    
    # 拟合线（线性回归）
    z = np.polyfit(y_true, y_pred, 1)
    p = np.poly1d(z)
    ax1.plot(y_true, p(y_true), 'b-', lw=2, alpha=0.7, label=f'拟合线: y={z[0]:.3f}x+{z[1]:.3f}')
    
    ax1.set_xlabel('实际值 (Actual)', fontsize=12)
    ax1.set_ylabel('预测值 (Predicted)', fontsize=12)
    ax1.set_title(f'{title}\nR²={r2:.4f}, RMSE={rmse:.4f}, MAE={mae:.4f}', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal', adjustable='box')
    
    # 右图：残差图
    residuals = y_true - y_pred
    ax2.scatter(y_pred, residuals, alpha=0.5, s=20, edgecolors='k', linewidths=0.5)
    ax2.axhline(y=0, color='r', linestyle='--', lw=2)
    ax2.set_xlabel('预测值 (Predicted)', fontsize=12)
    ax2.set_ylabel('残差 (Residuals)', fontsize=12)
    ax2.set_title('残差分布图', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight')
    print(f"拟合图已保存至: {save_path}")
    plt.show()  # 显示图表
    plt.close()


def plot_feature_importance(importances, feature_names, save_path='feature_importance.png'):
    """
    绘制特征重要性条形图
    
    参数:
    -----------
    importances : array-like
        特征重要性值
    feature_names : list
        特征名称列表
    save_path : str
        保存路径
    """
    # 创建DataFrame并排序
    fi_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values('importance', ascending=True)
    
    # 绘图
    plt.figure(figsize=(10, max(6, len(feature_names) * 0.4)))
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(fi_df)))
    plt.barh(fi_df['feature'], fi_df['importance'], color=colors, edgecolor='black', linewidth=0.5)
    plt.xlabel('特征重要性 (Feature Importance)', fontsize=12)
    plt.ylabel('特征 (Feature)', fontsize=12)
    plt.title('XGBoost 特征重要性排序', fontsize=14, fontweight='bold')
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight')
    print(f"特征重要性图已保存至: {save_path}")
    plt.close()


def train_xgboost(X, y, random_state=42, hyperparameter_tuning=True, n_iter=100):
    """训练 XGBoost 回归器并返回训练好的模型和预测结果（对测试集）。
    
    参数:
    -----------
    X : array-like
        特征矩阵
    y : array-like
        目标变量
    random_state : int
        随机种子
    hyperparameter_tuning : bool
        是否进行超参数调优
    n_iter : int
        随机搜索的迭代次数
    
    返回:
    -----------
    model : XGBRegressor
        训练好的模型
    splits : tuple
        (X_train, X_test, y_train, y_test)
    y_pred_test : array
        测试集预测值
    y_pred_all : array
        全部数据预测值
    best_params : dict or None
        最佳超参数（如果进行了调优）
    cv_results : dict or None
        交叉验证结果
    """
    try:
        from xgboost import XGBRegressor
    except Exception as e:
        raise ImportError("缺少 xgboost 库，请先安装：pip install xgboost") from e

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=random_state, shuffle=True)

    if hyperparameter_tuning:
        print("\n" + "="*60)
        print("开始XGBoost超参数调优（随机搜索）")
        print("="*60)
        
        # 定义超参数搜索空间
        param_distributions = {
            'n_estimators': [100, 200, 300, 500, 800, 1000],
            'learning_rate': [0.01, 0.03, 0.05, 0.07, 0.1, 0.15],
            'max_depth': [3, 4, 5, 6, 7, 8, 10],
            'min_child_weight': [1, 3, 5, 7],
            'subsample': [0.6, 0.7, 0.8, 0.9, 1.0],
            'colsample_bytree': [0.6, 0.7, 0.8, 0.9, 1.0],
            'gamma': [0, 0.1, 0.2, 0.3, 0.5],
            'reg_alpha': [0, 0.01, 0.1, 0.5, 1.0],
            'reg_lambda': [0.5, 1.0, 1.5, 2.0, 3.0]
        }
        
        # 基础模型
        base_model = XGBRegressor(random_state=random_state, verbosity=0)
        
        # 随机搜索
        random_search = RandomizedSearchCV(
            estimator=base_model,
            param_distributions=param_distributions,
            n_iter=n_iter,
            scoring='r2',
            cv=10,
            verbose=1,
            random_state=random_state,
            n_jobs=-1
        )

        print(f"开始随机搜索 {n_iter} 轮，使用 10 折交叉验证...")
        random_search.fit(X_train, y_train)
        
        print(f"\n最佳交叉验证 R² 分数: {random_search.best_score_:.4f}")
        print("\n最佳超参数:")
        for param, value in random_search.best_params_.items():
            print(f"  {param}: {value}")
        
        model = random_search.best_estimator_
        best_params = random_search.best_params_
        cv_results = {
            'best_score': random_search.best_score_,
            'cv_results': random_search.cv_results_
        }
    else:
        # 使用最佳超参数配置（200轮随机搜索结果）
        print("\n使用最佳超参数配置训练模型...")
        print("最佳超参数配置:")
        best_params_config = {
            'n_estimators': 1000,
            'learning_rate': 0.01,
            'max_depth': 4,
            'min_child_weight': 7,
            'subsample': 0.6,
            'colsample_bytree': 0.9,
            'gamma': 0.1,
            'reg_alpha': 0.01,
            'reg_lambda': 0.5
        }
        for param, value in best_params_config.items():
            print(f"  {param}: {value}")
        
        # 基础模型
        base_model = XGBRegressor(
            n_estimators=best_params_config['n_estimators'],
            learning_rate=best_params_config['learning_rate'],
            max_depth=best_params_config['max_depth'],
            min_child_weight=best_params_config['min_child_weight'],
            subsample=best_params_config['subsample'],
            colsample_bytree=best_params_config['colsample_bytree'],
            gamma=best_params_config['gamma'],
            reg_alpha=best_params_config['reg_alpha'],
            reg_lambda=best_params_config['reg_lambda'],
            random_state=random_state,
            verbosity=0
        )
        
        # 使用5折交叉验证评估模型
        from sklearn.model_selection import cross_val_score
        print("\n进行5折交叉验证...")
        cv_scores = cross_val_score(base_model, X_train, y_train, cv=5,scoring='r2', n_jobs=-1)
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()
        
        print(f"交叉验证 R² 分数:")
        for i, score in enumerate(cv_scores, 1):
            print(f"  Fold {i}: {score:.4f}")
        print(f"  平均值: {cv_mean:.4f} (±{cv_std:.4f})")
        
        # 在完整训练集上训练最终模型
        model = base_model.fit(X_train, y_train)
        best_params = best_params_config
        cv_results = {
            'cv_scores': cv_scores,
            'best_score': cv_mean,
            'std_score': cv_std
        }

    y_pred_test = model.predict(X_test)
    y_pred_all = model.predict(X)

    return model, (X_train, X_test, y_train, y_test), y_pred_test, y_pred_all, best_params, cv_results


def main():
    # 路径配置（可按需修改）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gtwr_script = os.path.join(project_root, 'Models', 'GTWR.py')
    gtwr_results = os.path.join(project_root, 'GTWR_results_improved.xlsx')

    # 创建Image和Sheet目录
    image_dir = 'Image'
    sheet_dir = 'Sheet'
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(sheet_dir, exist_ok=True)

    # 如果 GTWR.py 在 Models 下，GTWR_results.xlsx 默认会写到当前工作目录
    # 优先使用用户数据路径与变量定义（与 GTWR.py 保持一致）
    data_path = os.path.join(project_root, 'Data', 'Stations.xlsx')
    dependent_var = 'newSPEI3'
    independent_vars = ['DEM', 'Slope', 'Clay', 'Sand', 'LST_DIF',
                        'Pre', 'Tem', 'ET', 'SMCI', 'VCI', 'TCI', 'VPD', 'PCI3']

    # 确保 GTWR 结果存在
    ok = ensure_gtwr_results(gtwr_results, gtwr_script)
    if not ok:
        print("无法获取 GTWR 结果文件，退出。")
        return

    # 读取 GTWR 结果
    results_df = pd.read_excel(gtwr_results)
    print(f"读取 GTWR 结果，行数={len(results_df)} 列数={len(results_df.columns)}")

    # 构造特征
    features, vif_df, removed_vars, kept_vars = build_features(results_df, independent_vars, vif_threshold=10.0)
    print(f"VIF >=10 被剔除的变量: {removed_vars}")
    print(f"VIF <10 保留的变量: {kept_vars}")
    print(f"XGBoost 特征数: {len(features)}")

    # 检查必须列
    missing = [f for f in features if f not in results_df.columns]
    if len(missing) > 0:
        print("结果数据中缺少以下特征列，将尝试从原始数据读取补齐：", missing)
        # 读取原始数据以补齐列
        orig = pd.read_excel(data_path)
        for col in missing:
            if col in orig.columns:
                results_df[col] = orig[col]
            else:
                print(f"警告：原始数据也缺少列 {col}，将用 0 填充")
                results_df[col] = 0

    # 最终 X, y
    X = results_df[features].values
    y = results_df[dependent_var].values

    # 训练 XGBoost（使用最佳超参数配置）
    try:
        model, splits, y_pred_test, y_pred_all, best_params, cv_results = train_xgboost(
            X, y, 
            hyperparameter_tuning=False,  # 关闭超参数调优，使用预设的最佳参数
            n_iter=200  # 200轮随机搜索
        )
    except ImportError as e:
        print(e)
        print("请在终端运行：pip install xgboost openpyxl joblib")
        return

    X_train, X_test, y_train, y_test = splits

    # 评估
    r2 = r2_score(y_test, y_pred_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    mae = mean_absolute_error(y_test, y_pred_test)

    print('\n' + "="*60)
    print('XGBoost 测试集性能')
    print("="*60)
    print(f'  R² = {r2:.4f}')
    print(f'  RMSE = {rmse:.4f}')
    print(f'  MAE = {mae:.4f}')
    
    # 全集评估
    r2_all = r2_score(y, y_pred_all)
    rmse_all = np.sqrt(mean_squared_error(y, y_pred_all))
    mae_all = mean_absolute_error(y, y_pred_all)
    print('\n全数据集性能:')
    print(f'  R² = {r2_all:.4f}')
    print(f'  RMSE = {rmse_all:.4f}')
    print(f'  MAE = {mae_all:.4f}')

    # 绘制拟合散点图
    print("\n" + "="*60)
    print("生成可视化图表")
    print("="*60)
    
    # 测试集拟合图（临时显示）
    plot_path_test = os.path.join(image_dir, 'GTWR_XGBoost_fitting_test.png')
    plot_fitting_results(y_test, y_pred_test, title='XGBoost拟合效果（测试集）', save_path=plot_path_test)
    
    # 全数据集拟合图（临时显示）
    plot_path_all = os.path.join(image_dir, 'GTWR_XGBoost_fitting_all.png')
    plot_fitting_results(y, y_pred_all, title='XGBoost拟合效果（全数据集）', save_path=plot_path_all)

    # 保存预测结果
    results_df['gtwr_xgb_predicted_newSPEI3'] = y_pred_all
    results_df['gtwr_xgb_residual'] = results_df[dependent_var] - results_df['gtwr_xgb_predicted_newSPEI3']
    
    results_path = os.path.join(sheet_dir, 'GTWR_XGBoost_results.xlsx')
    results_df.to_excel(results_path, index=False)
    print(f"\n已保存预测结果到: {results_path}")

    # 保存超参数配置结果
    if best_params is not None:
        params_path = os.path.join(sheet_dir, 'GTWR_XGBoost_best_params.txt')
        with open(params_path, 'w', encoding='utf-8') as f:
            f.write("GTWR-XGBoost 最佳超参数配置\n")
            f.write("="*60 + "\n\n")
            if cv_results is not None:
                f.write(f"5折交叉验证 R² 分数: {cv_results['best_score']:.4f} (±{cv_results.get('std_score', 0):.4f})\n")
                if 'cv_scores' in cv_results:
                    f.write("\n各折得分:\n")
                    for i, score in enumerate(cv_results['cv_scores'], 1):
                        f.write(f"  Fold {i}: {score:.4f}\n")
                f.write("\n")
            f.write("使用的超参数:\n")
            for param, value in best_params.items():
                f.write(f"  {param}: {value}\n")
            f.write("\n测试集性能:\n")
            f.write(f"  R² = {r2:.4f}\n")
            f.write(f"  RMSE = {rmse:.4f}\n")
            f.write(f"  MAE = {mae:.4f}\n")
            f.write("\n全数据集性能:\n")
            f.write(f"  R² = {r2_all:.4f}\n")
            f.write(f"  RMSE = {rmse_all:.4f}\n")
            f.write(f"  MAE = {mae_all:.4f}\n")
        print(f"\n已保存超参数配置到: {params_path}")

    print('\n' + "="*60)
    print('分析完成！已显示拟合散点图')
    print("="*60)


if __name__ == "__main__":
    main()
