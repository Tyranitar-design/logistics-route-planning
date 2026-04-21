"""
可视化模块
==========

Pareto 前沿可视化、收敛曲线等

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class OptimizationVisualizer:
    """
    优化结果可视化器
    """
    
    @classmethod
    def plot_pareto_front(cls,
                          results: Dict,
                          save_path: Optional[str] = None,
                          show: bool = True):
        """
        绘制 Pareto 前沿
        
        Args:
            results: {求解器: OptimizationResult} 字典
            save_path: 保存路径
            show: 是否显示
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib 未安装，跳过可视化")
            return
        
        # 获取目标数
        first_result = list(results.values())[0]
        n_obj = len(first_result.objective_values)
        
        if n_obj == 2:
            # 2目标
            fig, ax = plt.subplots(figsize=(10, 8))
            
            colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
            
            for (solver_type, result), color in zip(results.items(), colors):
                ax.scatter(result.objective_values[0],
                          result.objective_values[1],
                          c=[color],
                          label=solver_type.value,
                          s=100,
                          alpha=0.7)
            
            ax.set_xlabel('目标1 (距离)', fontsize=12)
            ax.set_ylabel('目标2 (时间)', fontsize=12)
            ax.set_title('Pareto 前沿对比', fontsize=14)
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        elif n_obj == 3:
            # 3目标
            from mpl_toolkits.mplot3d import Axes3D
            
            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection='3d')
            
            colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
            
            for (solver_type, result), color in zip(results.items(), colors):
                ax.scatter(result.objective_values[0],
                          result.objective_values[1],
                          result.objective_values[2],
                          c=[color],
                          label=solver_type.value,
                          s=100,
                          alpha=0.7)
            
            ax.set_xlabel('目标1 (距离)', fontsize=10)
            ax.set_ylabel('目标2 (时间)', fontsize=10)
            ax.set_zlabel('目标3 (车辆数)', fontsize=10)
            ax.set_title('Pareto 前沿对比 (3D)', fontsize=14)
            ax.legend()
        
        else:
            # 高维：使用平行坐标图
            fig, ax = plt.subplots(figsize=(12, 8))
            
            colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
            
            for (solver_type, result), color in zip(results.items(), colors):
                ax.plot(range(n_obj), result.objective_values,
                       'o-', color=color, label=solver_type.value,
                       markersize=10, linewidth=2)
            
            ax.set_xlabel('目标索引', fontsize=12)
            ax.set_ylabel('目标值', fontsize=12)
            ax.set_title('多目标解对比 (平行坐标)', fontsize=14)
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图片已保存到: {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    @classmethod
    def plot_convergence(cls,
                        history: List[np.ndarray],
                        save_path: Optional[str] = None,
                        show: bool = True):
        """
        绘制收敛曲线
        
        Args:
            history: 每代最优目标值列表
            save_path: 保存路径
            show: 是否显示
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        history_array = np.array(history)
        n_gen = len(history)
        
        ax.plot(range(n_gen), history_array, 'b-', linewidth=2)
        ax.set_xlabel('迭代次数', fontsize=12)
        ax.set_ylabel('目标值', fontsize=12)
        ax.set_title('收敛曲线', fontsize=14)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    @classmethod
    def plot_comparison(cls,
                       results: Dict,
                       metrics: List[str] = ['objective', 'time'],
                       save_path: Optional[str] = None,
                       show: bool = True):
        """
        绘制求解器对比条形图
        
        Args:
            results: 结果字典
            metrics: 要对比的指标
            save_path: 保存路径
            show: 是否显示
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            return
        
        n_solvers = len(results)
        n_metrics = len(metrics)
        
        fig, axes = plt.subplots(1, n_metrics, figsize=(5*n_metrics, 6))
        
        if n_metrics == 1:
            axes = [axes]
        
        solver_names = [s.value for s in results.keys()]
        
        for ax, metric in zip(axes, metrics):
            if metric == 'objective':
                values = [r.primary_objective for r in results.values()]
                ylabel = '目标值'
            elif metric == 'time':
                values = [r.solve_time for r in results.values()]
                ylabel = '求解时间 (s)'
            elif metric == 'gap':
                values = [r.gap if r.gap else 0 for r in results.values()]
                ylabel = '最优间隙'
            else:
                continue
            
            colors = plt.cm.viridis(np.linspace(0.2, 0.8, n_solvers))
            bars = ax.bar(solver_names, values, color=colors)
            
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_title(f'{ylabel}对比', fontsize=14)
            ax.tick_params(axis='x', rotation=45)
            
            # 添加数值标签
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                       f'{val:.2f}', ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    @classmethod
    def generate_report_html(cls,
                            comparison_result,
                            save_path: str) -> str:
        """
        生成 HTML 格式的对比报告
        
        Args:
            comparison_result: ComparisonResult 对象
            save_path: 保存路径
        
        Returns:
            HTML 文件路径
        """
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>优化结果对比报告</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            background: white;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .best { background-color: #dff0d8; font-weight: bold; }
        .metric-card {
            background: white;
            padding: 20px;
            margin: 10px 0;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <h1>🔍 优化结果对比报告</h1>
    <p>生成时间: 2026-04-19</p>
    
    <h2>📊 排名总览</h2>
    <table>
        <tr>
            <th>排名</th>
            <th>求解器</th>
            <th>目标值</th>
            <th>求解时间</th>
            <th>最优间隙</th>
        </tr>
"""
        
        for rank, (solver_type, score) in enumerate(comparison_result.rankings, 1):
            result = comparison_result.solver_results[solver_type]
            is_best = "class='best'" if rank == 1 else ""
            
            html += f"""
        <tr {is_best}>
            <td>{rank}</td>
            <td>{solver_type.value}</td>
            <td>{result.primary_objective:.2f}</td>
            <td>{result.solve_time:.2f}s</td>
            <td>{result.gap:.2%}" if result.gap else "N/A"</td>
        </tr>
"""
        
        html += """
    </table>
    
    <h2>🏆 最佳求解器</h2>
    <div class="metric-card">
"""
        
        if comparison_result.best_solver:
            best_result = comparison_result.solver_results[comparison_result.best_solver]
            html += f"""
        <h3>推荐: {comparison_result.best_solver.value}</h3>
        <p><strong>目标值:</strong> {best_result.objective_values}</p>
        <p><strong>求解时间:</strong> {best_result.solve_time:.2f}s</p>
        <p><strong>路线数:</strong> {len(best_result.routes)}</p>
"""
        
        html += """
    </div>
    
    <h2>📈 详细指标</h2>
"""
        
        for metric_name, values in comparison_result.metrics.items():
            html += f"""
    <div class="metric-card">
        <h3>{metric_name}</h3>
        <ul>
"""
            for solver_type, value in values.items():
                html += f"            <li>{solver_type.value}: {value:.4f}</li>\n"
            html += "        </ul>\n    </div>\n"
        
        html += """
</body>
</html>
"""
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return save_path
