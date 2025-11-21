#!/usr/bin/env python3
"""
REFORM vs Baseline 数据汇总表格
==============================
生成清晰的对比数据表格
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from pathlib import Path

# 设置字体
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10

# 创建图表
fig, ax = plt.subplots(figsize=(14, 10))
ax.axis('off')

# 定义颜色
header_color = '#34495e'
baseline_color = '#3498db'
reform_color = '#e74c3c'
better_color = '#d5f4e6'
worse_color = '#fadbd8'
neutral_color = '#f8f9fa'

# 表格数据
table_data = [
    ['Metric', 'Baseline RAG', 'REFORM RAG', 'Change', 'Interpretation'],
    ['', '', '', '', ''],
    ['Performance Metrics', '', '', '', ''],
    ['F1 Score', '0.3250 (32.5%)', '0.2486 (24.86%)', '-23.5%', '❌ Accuracy decreased'],
    ['Token Count', '17,038 tokens', '1,571 tokens', '-90.8%', '✅ Massive reduction'],
    ['Compression Rate', '1.0×', '10.81×', '+981%', '✅ 10.8× compression'],
    ['', '', '', '', ''],
    ['Latency Breakdown', '', '', '', ''],
    ['Retrieve Time', '25.36s (58.0%)', '31.49s (68.2%)', '+24.2%', '❌ Slower retrieval'],
    ['Refine Time', '0.00s (0.0%)', '13.94s (30.2%)', '+∞', '❌ New overhead'],
    ['Generate Time', '4.98s (42.0%)', '0.73s (1.6%)', '-85.3%', '✅ Much faster'],
    ['Total Latency', '30.33s', '46.16s', '+52.2%', '❌ Slower overall'],
    ['', '', '', '', ''],
    ['Answer Quality Distribution', '', '', '', ''],
    ['Perfect (F1=1.0)', '3/10 (30%)', '2/10 (20%)', '-33%', '❌ Fewer perfect answers'],
    ['Partial (0<F1<1)', '1/10 (10%)', '3/10 (30%)', '+200%', '⚠️ More partial matches'],
    ['Failed (F1=0)', '6/10 (60%)', '5/10 (50%)', '-17%', '✅ Fewer failures'],
]

# 创建表格
table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                colWidths=[0.22, 0.20, 0.20, 0.13, 0.25])

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.2)

# 设置样式
for i, row in enumerate(table_data):
    for j, cell_text in enumerate(row):
        cell = table[(i, j)]
        
        # 标题行
        if i == 0:
            cell.set_facecolor(header_color)
            cell.set_text_props(weight='bold', color='white', fontsize=11)
            cell.set_height(0.06)
        
        # 分组标题
        elif i in [2, 7, 13]:
            cell.set_facecolor('#95a5a6')
            cell.set_text_props(weight='bold', color='white', fontsize=10)
            cell.set_height(0.05)
        
        # 空行
        elif i in [1, 6, 12]:
            cell.set_facecolor(neutral_color)
            cell.set_height(0.03)
        
        # 数据行
        else:
            # Baseline列
            if j == 1:
                cell.set_facecolor(baseline_color + '30')
                cell.set_text_props(fontsize=9.5)
            # REFORM列
            elif j == 2:
                cell.set_facecolor(reform_color + '30')
                cell.set_text_props(fontsize=9.5)
            # Change列
            elif j == 3:
                if cell_text.startswith('-') and i not in [3, 11]:  # 负数且不是F1/Latency
                    cell.set_facecolor(better_color)
                    cell.set_text_props(color='#27ae60', weight='bold', fontsize=9.5)
                elif cell_text.startswith('+') and i in [5]:  # 正数且是Compression
                    cell.set_facecolor(better_color)
                    cell.set_text_props(color='#27ae60', weight='bold', fontsize=9.5)
                elif cell_text.startswith('-') and i in [3, 11]:  # F1/Total降低
                    cell.set_facecolor(worse_color)
                    cell.set_text_props(color='#c0392b', weight='bold', fontsize=9.5)
                elif cell_text.startswith('+'):  # 其他增加
                    cell.set_facecolor(worse_color)
                    cell.set_text_props(color='#c0392b', weight='bold', fontsize=9.5)
                else:
                    cell.set_facecolor(neutral_color)
                    cell.set_text_props(fontsize=9.5)
            # Interpretation列
            elif j == 4:
                cell.set_facecolor(neutral_color)
                if '✅' in cell_text:
                    cell.set_text_props(color='#27ae60', fontsize=9)
                elif '❌' in cell_text:
                    cell.set_text_props(color='#c0392b', fontsize=9)
                elif '⚠️' in cell_text:
                    cell.set_text_props(color='#f39c12', fontsize=9)
                else:
                    cell.set_text_props(fontsize=9)
            # Metric列
            else:
                cell.set_facecolor(neutral_color)
                cell.set_text_props(fontsize=9.5)

# 添加标题
title_text = 'REFORM vs Baseline RAG: Detailed Performance Comparison'
subtitle_text = 'Dataset: Natural Questions (10 samples) | Model: Llama-3.1-8B-Instruct | Retrieval: Wiki18 FAISS (Top-8)'

plt.text(0.5, 0.98, title_text, transform=fig.transFigure,
         ha='center', va='top', fontsize=15, fontweight='bold')
plt.text(0.5, 0.95, subtitle_text, transform=fig.transFigure,
         ha='center', va='top', fontsize=10, color='#555')

# 添加图例
legend_elements = [
    mpatches.Patch(facecolor=better_color, edgecolor='black', label='Positive Change'),
    mpatches.Patch(facecolor=worse_color, edgecolor='black', label='Negative Change'),
    mpatches.Patch(facecolor=baseline_color + '30', edgecolor='black', label='Baseline Values'),
    mpatches.Patch(facecolor=reform_color + '30', edgecolor='black', label='REFORM Values'),
]
plt.legend(handles=legend_elements, loc='lower center', ncol=4, 
          bbox_to_anchor=(0.5, -0.03), frameon=True, fontsize=9)

# 添加关键发现框
findings_text = """
Key Findings:
• REFORM achieves 10.8× compression but sacrifices 23.5% F1 score
• Generate time reduced by 85.3% (4.98s → 0.73s) 
• Total latency increased by 52.2% due to Refine overhead (13.94s)
• Trade-off: Token efficiency ↑ vs Accuracy ↓ and Speed ↓
"""

bbox_props = dict(boxstyle='round,pad=0.8', facecolor='#fff9e6', 
                  edgecolor='#f39c12', linewidth=2)
plt.text(0.98, 0.12, findings_text, transform=fig.transFigure,
         ha='right', va='bottom', fontsize=9, family='monospace',
         bbox=bbox_props)

# 保存
output_dir = Path(__file__).parent
output_path = output_dir / 'reform_vs_baseline_table.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ 表格已保存到: {output_path}")

output_path_pdf = output_dir / 'reform_vs_baseline_table.pdf'
plt.savefig(output_path_pdf, bbox_inches='tight', facecolor='white')
print(f"✅ PDF已保存到: {output_path_pdf}")

plt.show()
