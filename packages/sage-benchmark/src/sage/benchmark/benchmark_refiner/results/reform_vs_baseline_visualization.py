#!/usr/bin/env python3
"""
REFORM vs Baseline RAG 对比可视化
==================================
生成综合对比图表，包括性能指标、时间分析和F1分布
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 数据定义
performance_metrics = {
    "F1 Score": {"Baseline": 0.3250, "REFORM": 0.2486},
    "Token Count": {"Baseline": 17038, "REFORM": 1571},
    "Compression Rate": {"Baseline": 1.0, "REFORM": 10.81},
}

latency_metrics = {
    "Retrieve": {"Baseline": 25.36, "REFORM": 31.49},
    "Refine": {"Baseline": 0.00, "REFORM": 13.94},
    "Generate": {"Baseline": 4.98, "REFORM": 0.73},
}

f1_distribution = {
    "Perfect (1.0)": {"Baseline": 30, "REFORM": 20},
    "Partial (0-1)": {"Baseline": 10, "REFORM": 30},
    "Failed (0.0)": {"Baseline": 60, "REFORM": 50},
}

# 创建图表
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

# 颜色方案
baseline_color = '#3498db'  # 蓝色
reform_color = '#e74c3c'    # 红色
positive_color = '#2ecc71'  # 绿色
negative_color = '#e67e22'  # 橙色

# ==================== 图1: F1 Score 对比 ====================
ax1 = fig.add_subplot(gs[0, 0])
metrics = ['F1 Score']
baseline_vals = [performance_metrics['F1 Score']['Baseline']]
reform_vals = [performance_metrics['F1 Score']['REFORM']]

x = np.arange(len(metrics))
width = 0.35

bars1 = ax1.bar(x - width/2, baseline_vals, width, label='Baseline', 
                color=baseline_color, alpha=0.8, edgecolor='black', linewidth=1.5)
bars2 = ax1.bar(x + width/2, reform_vals, width, label='REFORM', 
                color=reform_color, alpha=0.8, edgecolor='black', linewidth=1.5)

ax1.set_ylabel('F1 Score', fontsize=11, fontweight='bold')
ax1.set_title('(A) Answer Quality Comparison', fontsize=12, fontweight='bold', pad=10)
ax1.set_xticks(x)
ax1.set_xticklabels(metrics, fontsize=10)
ax1.legend(fontsize=10, loc='upper right')
ax1.grid(axis='y', alpha=0.3, linestyle='--')
ax1.set_ylim(0, 0.4)

# 添加数值标签
for bar in bars1 + bars2:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.4f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 添加变化百分比
change_pct = -23.5
ax1.text(0, 0.37, f'{change_pct:+.1f}%', ha='center', va='center',
         fontsize=10, color='red', fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='red', linewidth=2))

# ==================== 图2: Token Count 对比 ====================
ax2 = fig.add_subplot(gs[0, 1])
metrics = ['Token Count']
baseline_vals = [performance_metrics['Token Count']['Baseline']]
reform_vals = [performance_metrics['Token Count']['REFORM']]

x = np.arange(len(metrics))
bars1 = ax2.bar(x - width/2, baseline_vals, width, label='Baseline', 
                color=baseline_color, alpha=0.8, edgecolor='black', linewidth=1.5)
bars2 = ax2.bar(x + width/2, reform_vals, width, label='REFORM', 
                color=reform_color, alpha=0.8, edgecolor='black', linewidth=1.5)

ax2.set_ylabel('Token Count', fontsize=11, fontweight='bold')
ax2.set_title('(B) Context Size Comparison', fontsize=12, fontweight='bold', pad=10)
ax2.set_xticks(x)
ax2.set_xticklabels(metrics, fontsize=10)
ax2.legend(fontsize=10, loc='upper right')
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# 添加数值标签
for bar in bars1 + bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height):,}', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 添加压缩率标注
compression = performance_metrics['Token Count']['Baseline'] / performance_metrics['Token Count']['REFORM']
ax2.text(0, max(baseline_vals)*0.85, f'Compression:\n{compression:.1f}×', 
         ha='center', va='center', fontsize=11, color=positive_color, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=positive_color, linewidth=2))

# ==================== 图3: 时间堆叠柱状图 ====================
ax3 = fig.add_subplot(gs[0, 2])

retrieve_baseline = latency_metrics['Retrieve']['Baseline']
refine_baseline = latency_metrics['Refine']['Baseline']
generate_baseline = latency_metrics['Generate']['Baseline']

retrieve_reform = latency_metrics['Retrieve']['REFORM']
refine_reform = latency_metrics['Refine']['REFORM']
generate_reform = latency_metrics['Generate']['REFORM']

categories = ['Baseline', 'REFORM']
retrieve_data = [retrieve_baseline, retrieve_reform]
refine_data = [refine_baseline, refine_reform]
generate_data = [generate_baseline, generate_reform]

x = np.arange(len(categories))
width = 0.5

p1 = ax3.bar(x, retrieve_data, width, label='Retrieve', color='#3498db', edgecolor='black', linewidth=1.5)
p2 = ax3.bar(x, refine_data, width, bottom=retrieve_data, label='Refine', color='#e74c3c', edgecolor='black', linewidth=1.5)
p3 = ax3.bar(x, generate_data, width, 
             bottom=np.array(retrieve_data) + np.array(refine_data),
             label='Generate', color='#2ecc71', edgecolor='black', linewidth=1.5)

ax3.set_ylabel('Time (seconds)', fontsize=11, fontweight='bold')
ax3.set_title('(C) Latency Breakdown', fontsize=12, fontweight='bold', pad=10)
ax3.set_xticks(x)
ax3.set_xticklabels(categories, fontsize=10)
ax3.legend(fontsize=9, loc='upper left')
ax3.grid(axis='y', alpha=0.3, linestyle='--')

# 添加总时间标签
total_baseline = retrieve_baseline + refine_baseline + generate_baseline
total_reform = retrieve_reform + refine_reform + generate_reform
ax3.text(0, total_baseline + 2, f'{total_baseline:.1f}s', ha='center', va='bottom', 
         fontsize=10, fontweight='bold')
ax3.text(1, total_reform + 2, f'{total_reform:.1f}s', ha='center', va='bottom', 
         fontsize=10, fontweight='bold')

# ==================== 图4: 时间占比饼图 (Baseline) ====================
ax4 = fig.add_subplot(gs[1, 0])

sizes = [retrieve_baseline, generate_baseline]  # refine_baseline = 0
labels = [f'Retrieve\n{retrieve_baseline:.1f}s\n(58.0%)', 
          f'Generate\n{generate_baseline:.1f}s\n(42.0%)']
colors = ['#3498db', '#2ecc71']
explode = (0.05, 0.05)

wedges, texts, autotexts = ax4.pie(sizes, explode=explode, labels=labels, colors=colors,
                                     autopct='', startangle=90, textprops={'fontsize': 9, 'fontweight': 'bold'})

ax4.set_title('(D) Baseline Time Distribution', fontsize=12, fontweight='bold', pad=10)

# ==================== 图5: 时间占比饼图 (REFORM) ====================
ax5 = fig.add_subplot(gs[1, 1])

sizes = [retrieve_reform, refine_reform, generate_reform]
labels = [f'Retrieve\n{retrieve_reform:.1f}s\n(68.2%)', 
          f'Refine\n{refine_reform:.1f}s\n(30.2%)',
          f'Generate\n{generate_reform:.1f}s\n(1.6%)']
colors = ['#3498db', '#e74c3c', '#2ecc71']
explode = (0.05, 0.05, 0.05)

wedges, texts, autotexts = ax5.pie(sizes, explode=explode, labels=labels, colors=colors,
                                     autopct='', startangle=90, textprops={'fontsize': 9, 'fontweight': 'bold'})

ax5.set_title('(E) REFORM Time Distribution', fontsize=12, fontweight='bold', pad=10)

# ==================== 图6: F1 Score 分布堆叠条形图 ====================
ax6 = fig.add_subplot(gs[1, 2])

categories = ['Baseline', 'REFORM']
perfect = [f1_distribution['Perfect (1.0)']['Baseline'], f1_distribution['Perfect (1.0)']['REFORM']]
partial = [f1_distribution['Partial (0-1)']['Baseline'], f1_distribution['Partial (0-1)']['REFORM']]
failed = [f1_distribution['Failed (0.0)']['Baseline'], f1_distribution['Failed (0.0)']['REFORM']]

x = np.arange(len(categories))
width = 0.5

p1 = ax6.bar(x, perfect, width, label='Perfect (1.0)', color='#2ecc71', edgecolor='black', linewidth=1.5)
p2 = ax6.bar(x, partial, width, bottom=perfect, label='Partial (0-1)', color='#f39c12', edgecolor='black', linewidth=1.5)
p3 = ax6.bar(x, failed, width, bottom=np.array(perfect) + np.array(partial), 
             label='Failed (0.0)', color='#e74c3c', edgecolor='black', linewidth=1.5)

ax6.set_ylabel('Percentage (%)', fontsize=11, fontweight='bold')
ax6.set_title('(F) F1 Score Distribution', fontsize=12, fontweight='bold', pad=10)
ax6.set_xticks(x)
ax6.set_xticklabels(categories, fontsize=10)
ax6.legend(fontsize=9, loc='upper left')
ax6.set_ylim(0, 105)
ax6.grid(axis='y', alpha=0.3, linestyle='--')

# 添加百分比标签
for i, (p, pa, f) in enumerate(zip(perfect, partial, failed)):
    if p > 5:
        ax6.text(i, p/2, f'{p}%', ha='center', va='center', fontsize=9, fontweight='bold', color='white')
    if pa > 5:
        ax6.text(i, p + pa/2, f'{pa}%', ha='center', va='center', fontsize=9, fontweight='bold', color='white')
    if f > 5:
        ax6.text(i, p + pa + f/2, f'{f}%', ha='center', va='center', fontsize=9, fontweight='bold', color='white')

# ==================== 图7: 关键指标对比雷达图 ====================
ax7 = fig.add_subplot(gs[2, :], projection='polar')

categories = ['F1 Score\n(↑)', 'Token\nEfficiency\n(↑)', 'Speed\n(↑)', 
              'Accuracy\n(↑)', 'Cost\nSaving\n(↑)']
N = len(categories)

# 归一化指标 (0-100)
baseline_values = [
    32.5,  # F1 Score (直接用百分比)
    100 - (17038/17038)*100,  # Token效率 (越少越好,但baseline作为基准0)
    (1/30.33)*100*30,  # 速度 (1/latency归一化)
    30.0,  # 准确率 (完全正确的百分比)
    0,  # 成本节省 (baseline无节省)
]

reform_values = [
    24.86,  # F1 Score
    100 - (1571/17038)*100,  # Token效率 (相比baseline节省90.8%)
    (1/46.16)*100*30,  # 速度
    20.0,  # 准确率
    90.8,  # 成本节省 (token减少90.8%)
]

angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
baseline_values += baseline_values[:1]
reform_values += reform_values[:1]
angles += angles[:1]

ax7.plot(angles, baseline_values, 'o-', linewidth=2, label='Baseline', color=baseline_color)
ax7.fill(angles, baseline_values, alpha=0.25, color=baseline_color)
ax7.plot(angles, reform_values, 'o-', linewidth=2, label='REFORM', color=reform_color)
ax7.fill(angles, reform_values, alpha=0.25, color=reform_color)

ax7.set_xticks(angles[:-1])
ax7.set_xticklabels(categories, fontsize=10)
ax7.set_ylim(0, 100)
ax7.set_title('(G) Multi-Dimensional Performance Radar', fontsize=12, fontweight='bold', pad=20, y=1.08)
ax7.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
ax7.grid(True, linestyle='--', alpha=0.5)

# 添加总标题
fig.suptitle('REFORM vs Baseline RAG: Comprehensive Performance Analysis\n' + 
             'Dataset: Natural Questions (10 samples) | Model: Llama-3.1-8B-Instruct | Retrieval: Wiki18 FAISS (Top-8)',
             fontsize=14, fontweight='bold', y=0.98)

# 保存图表
output_dir = Path(__file__).parent
output_path = output_dir / 'reform_vs_baseline_comparison.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ 图表已保存到: {output_path}")

# 也保存PDF版本
output_path_pdf = output_dir / 'reform_vs_baseline_comparison.pdf'
plt.savefig(output_path_pdf, bbox_inches='tight', facecolor='white')
print(f"✅ PDF已保存到: {output_path_pdf}")

plt.show()
