"""
随机森林（Random Forest）模型
用于预测 newSPEI3

说明：
- 直接使用所有原始变量进行预测，不进行VIF和相关系数检验
- 训练随机森林回归模型
- 评估模型性能并生成拟合散点图

使用：
    python Models/RF.py

依赖：pandas, numpy, scikit-learn, openpyxl, matplotlib
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
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


def load_data(file_path):
    """
    加载数据
    
    参数:
    -----------
    file_path : str
        数据文件路径
    
    返回:
    -----------
    df : DataFrame
        加载的数据
    """
    print("正在加载数据...")
    df = pd.read_excel(file_path)
    print(f"数据加载完成！形状: {df.shape}")
    
    # 删除缺失值
    print(f"删除前数据量: {len(df)}")
    df = df.dropna(subset=['newSPEI3'])
    print(f"删除缺失值后数据量: {len(df)}")
    
    return df


def plot_fitting_results(y_true, y_pred, title='Random Forest拟合效果', save_path='RF_fitting.png'):
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


def plot_feature_importance(importances, feature_names, save_path='RF_feature_importance.png'):
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
    plt.title('Random Forest 特征重要性排序', fontsize=14, fontweight='bold')
    plt.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight')
    print(f"特征重要性图已保存至: {save_path}")
    plt.show()
    plt.close()


def train_random_forest(X, y, random_state=42, hyperparameter_tuning=True, n_iter=200):
    """
    训练 Random Forest 回归器
    
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
    model : RandomForestRegressor
        训练好的模型
    splits : tuple
        (X_train, X_test, y_train, y_test)
    y_pred_test : array
        测试集预测值
    y_pred_all : array
        全部数据预测值
    best_params : dict or None
        最佳超参数
    cv_results : dict or None
        交叉验证结果
    """
    # 80/20 分割（不打乱数据）
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=random_state, shuffle=True)
    
    print(f"\n数据集划分:")
    print(f"  训练集: {len(X_train)} 样本")
    print(f"  测试集: {len(X_test)} 样本")

    if hyperparameter_tuning:
        print("\n" + "="*60)
        print("开始Random Forest超参数调优（随机搜索）")
        print("="*60)
        
        # 定义超参数搜索空间
        param_distributions = {
            'n_estimators': [100, 200, 300, 500, 800, 1000],
            'max_depth': [10, 20, 30, 40, 50, None],
            'min_samples_split': [2, 5, 10, 15, 20],
            'min_samples_leaf': [1, 2, 4, 6, 8],
            'max_features': ['sqrt', 'log2', 0.3, 0.5, 0.7],
            'bootstrap': [True, False],
            'max_samples': [0.6, 0.7, 0.8, 0.9, None]
        }
        
        # 基础模型
        base_model = RandomForestRegressor(random_state=random_state, n_jobs=-1)
        
        # 随机搜索
        random_search = RandomizedSearchCV(
            estimator=base_model,
            param_distributions=param_distributions,
            n_iter=n_iter,
            scoring='r2',
            cv=5,
            verbose=1,
            random_state=random_state,
            n_jobs=-1
        )
        
        print(f"开始随机搜索 {n_iter} 轮，使用 5 折交叉验证...")
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
        # 使用默认参数
        print("\n使用默认参数训练模型...")
        model = RandomForestRegressor(
            n_estimators=500,
            max_depth=30,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=random_state,
            n_jobs=-1,
            verbose=0
        )
        model.fit(X_train, y_train)
        best_params = None
        cv_results = None

    y_pred_test = model.predict(X_test)
    y_pred_all = model.predict(X)

    return model, (X_train, X_test, y_train, y_test), y_pred_test, y_pred_all, best_params, cv_results


def main():
    # 路径配置
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(project_root, 'Data', 'Stations.xlsx')
    image_dir = 'Image'
    sheet_dir = 'Sheet'
    
    # 创建Image和Sheet目录（如果不存在）
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(sheet_dir, exist_ok=True)
    
    # 定义变量
    dependent_var = 'newSPEI3'
    independent_vars = ['DEM', 'Slope', 'Clay', 'Sand', 'LST_DIF',
                     'Tem', 'ET', 'SMCI', 'VCI', 'TCI', 'VPD', 'PCI3']
    
    print("="*60)
    print("随机森林（Random Forest）回归模型")
    print("="*60)
    
    # 加载数据
    df = load_data(data_path)
    
    # 准备特征和目标变量
    print(f"\n特征变量 ({len(independent_vars)}个):")
    for var in independent_vars:
        print(f"  - {var}")
    print(f"\n目标变量: {dependent_var}")
    
    X = df[independent_vars].values
    y = df[dependent_var].values
    
    # 训练 Random Forest（启用超参数调优）
    model, splits, y_pred_test, y_pred_all, best_params, cv_results = train_random_forest(
        X, y, 
        hyperparameter_tuning=False,  # 启用超参数调优
        n_iter=200  # 200轮随机搜索
    )
    
    X_train, X_test, y_train, y_test = splits
    
    # 评估
    r2 = r2_score(y_test, y_pred_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    mae = mean_absolute_error(y_test, y_pred_test)
    
    print('\n' + "="*60)
    print('Random Forest 测试集性能')
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
    
    # 测试集拟合图
    plot_path_test = os.path.join(image_dir, 'RF_fitting_test.png')
    plot_fitting_results(y_test, y_pred_test, title='Random Forest拟合效果（测试集）', save_path=plot_path_test)
    
    # 全数据集拟合图
    plot_path_all = os.path.join(image_dir, 'RF_fitting_all.png')
    plot_fitting_results(y, y_pred_all, title='Random Forest拟合效果（全数据集）', save_path=plot_path_all)
    
    # 特征重要性
    importances = model.feature_importances_
    fi_df = pd.DataFrame({
        'feature': independent_vars,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    fi_path = os.path.join(sheet_dir, 'RF_feature_importance.csv')
    fi_df.to_csv(fi_path, index=False)
    print(f"\n已保存特征重要性到: {fi_path}")
    
    # 绘制特征重要性图
    fi_plot_path = os.path.join(image_dir, 'RF_feature_importance.png')
    plot_feature_importance(importances, independent_vars, save_path=fi_plot_path)
    
    # 保存模型
    model_path = os.path.join(sheet_dir, 'RF_model.joblib')
    joblib.dump(model, model_path)
    print(f"已保存模型到: {model_path}")
    
    # 保存预测结果
    results_df = df.copy()
    results_df['rf_predicted_newSPEI3'] = y_pred_all
    results_df['rf_residual'] = results_df[dependent_var] - results_df['rf_predicted_newSPEI3']
    
    # 标记测试集(用于后续对比)
    results_df['is_test'] = False
    _, test_indices = train_test_split(
        np.arange(len(results_df)), 
        test_size=0.2, 
        random_state=42, 
        shuffle=True
    )
    results_df.iloc[test_indices, results_df.columns.get_loc('is_test')] = True
    
    results_path = os.path.join(sheet_dir, 'RF_results.xlsx')
    results_df.to_excel(results_path, index=False)
    print(f"已保存预测结果到: {results_path}")
    
    # 保存超参数调优结果
    if best_params is not None:
        params_path = os.path.join(sheet_dir, 'RF_best_params.txt')
        with open(params_path, 'w', encoding='utf-8') as f:
            f.write("Random Forest 最佳超参数 (200轮随机搜索)\n")
            f.write("="*60 + "\n\n")
            f.write(f"最佳交叉验证 R² 分数: {cv_results['best_score']:.4f}\n\n")
            f.write("最佳超参数:\n")
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
        print(f"已保存最佳超参数到: {params_path}")
    
    print('\n' + "="*60)
    print('分析完成！')
    print("="*60)
    print('\n生成的文件:')
    print(f'  - 模型文件: RF_model.joblib')
    print(f'  - 预测结果: RF_results.xlsx')
    print(f'  - 特征重要性: RF_feature_importance.csv')
    print(f'  - 特征重要性图: RF_feature_importance.png')
    print(f'  - 拟合图（测试集）: RF_fitting_test.png')
    print(f'  - 拟合图（全集）: RF_fitting_all.png')
    if best_params is not None:
        print(f'  - 最佳超参数: RF_best_params.txt')
    
    return model, results_df, fi_df


if __name__ == "__main__":
    model, results, feature_importance = main()
