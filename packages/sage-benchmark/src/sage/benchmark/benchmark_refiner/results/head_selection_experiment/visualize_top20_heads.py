"""
可视化Top 20 Attention Heads的MNR性能
======================================

创建清晰、易于区分的可视化图表
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
sns.set_palette("husl")

# 读取数据
df = pd.read_csv('head_mnr_wiki18_local.csv')

# 选择Top 20
top20 = df.nsmallest(20, 'mnr').copy()

# 创建标签
top20['label'] = top20.apply(
    lambda x: f"L{x['layer']:02d}H{x['head']:02d}-{x['head_type']}", 
    axis=1
)

# ==================== 主图：排名条形图 + 层分布散点图 ====================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
fig.suptitle('Top 20 Attention Heads for Retrieval Performance', 
             fontsize=18, fontweight='bold', y=0.98)


# ==================== 图1: 横向条形图 (MNR排名) ====================
colors = ['#e74c3c' if t == 'Q' else '#3498db' if t == 'K' else '#2ecc71' 
          for t in top20['head_type']]
y_pos = np.arange(len(top20))

bars = ax1.barh(y_pos, top20['mnr'], color=colors, alpha=0.85, 
                edgecolor='black', linewidth=1.2, height=0.75)

# 添加渐变效果（模拟）
for i, bar in enumerate(bars):
    bar.set_alpha(0.75 + 0.25 * (1 - i / len(bars)))

ax1.set_yticks(y_pos)
ax1.set_yticklabels(top20['label'], fontsize=10, fontweight='bold')
ax1.set_xlabel('Mean Normalized Rank (MNR)', fontsize=13, fontweight='bold')
ax1.set_title('MNR Score Ranking (Lower is Better)', 
              fontsize=14, fontweight='bold', pad=15)
ax1.invert_yaxis()
ax1.grid(axis='x', alpha=0.4, linestyle='--')
ax1.set_xlim(0.23, 0.28)

# 添加数值标签
for i, (mnr, std) in enumerate(zip(top20['mnr'], top20['mnr_std'])):
    ax1.text(mnr + 0.001, i, f'{mnr:.4f}', 
             va='center', ha='left', fontsize=8.5, fontweight='bold')

# 添加图例
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#e74c3c', edgecolor='black', label='Query (Q)', alpha=0.85),
    Patch(facecolor='#3498db', edgecolor='black', label='Key (K)', alpha=0.85),
    Patch(facecolor='#2ecc71', edgecolor='black', label='Value (V)', alpha=0.85)
]
ax1.legend(handles=legend_elements, loc='lower right', fontsize=11, 
          framealpha=0.95, edgecolor='black')

# 添加标注线指向最佳head
best_y = 0
ax1.annotate('Best Head', xy=(top20.iloc[0]['mnr'], best_y), 
            xytext=(0.24, best_y),
            arrowprops=dict(arrowstyle='->', lw=2, color='red'),
            fontsize=11, fontweight='bold', color='red',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))

# ==================== 图2: 层分布散点图 ====================
# 按类型分组绘制
for head_type, color, marker, size in [
    ('Q', '#e74c3c', 'o', 250), 
    ('K', '#3498db', 's', 250), 
    ('V', '#2ecc71', '^', 280)
]:
    mask = top20['head_type'] == head_type
    subset = top20[mask]
    
    if len(subset) > 0:
        # 绘制散点
        scatter = ax2.scatter(subset['layer'], subset['mnr'], 
                   c=color, marker=marker, s=size, alpha=0.75, 
                   edgecolors='black', linewidths=2, label=f'{head_type} ({len(subset)})',
                   zorder=3)
        
        # 添加头编号标注
        for _, row in subset.iterrows():
            ax2.annotate(f"{row['head']}", 
                        (row['layer'], row['mnr']),
                        xytext=(0, 0), textcoords='offset points',
                        fontsize=9, fontweight='bold', ha='center', va='center',
                        color='white' if head_type == 'Q' else 'black')

ax2.set_xlabel('Layer Index', fontsize=13, fontweight='bold')
ax2.set_ylabel('Mean Normalized Rank (MNR)', fontsize=13, fontweight='bold')
ax2.set_title('Layer Distribution of Top 20 Heads', 
              fontsize=14, fontweight='bold', pad=15)
ax2.legend(fontsize=11, loc='upper right', framealpha=0.95, edgecolor='black')
ax2.grid(True, alpha=0.4, linestyle='--', zorder=1)
ax2.set_xticks(range(0, 32, 2))
ax2.set_xlim(-1, 32)
ax2.set_ylim(0.23, 0.27)

# 高亮中间层区域
ax2.axvspan(10, 18, alpha=0.1, color='green', zorder=0)
ax2.text(14, 0.268, 'Middle Layers\n(Most Effective)', 
         ha='center', va='top', fontsize=10, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.6))

plt.tight_layout()
plt.savefig('top20_heads_analysis.png', dpi=300, bbox_inches='tight')
plt.savefig('top20_heads_analysis.pdf', bbox_inches='tight')
print("✓ Saved: top20_heads_analysis.png")
print("✓ Saved: top20_heads_analysis.pdf")
plt.show()

# ==================== 打印统计信息 ====================
print("\n" + "="*70)
print("📊 Top 20 Attention Heads Statistics")
print("="*70)
print(f"\n🏆 Best Head:")
print(f"   Layer {top20.iloc[0]['layer']}, Head {top20.iloc[0]['head']} ({top20.iloc[0]['head_type']})")
print(f"   MNR: {top20.iloc[0]['mnr']:.5f} ± {top20.iloc[0]['mnr_std']:.4f}")

print(f"\n📈 Type Distribution:")
type_counts = top20['head_type'].value_counts()
for head_type, count in type_counts.items():
    print(f"   {head_type}: {count:2d} ({count/len(top20)*100:5.1f}%)")

print(f"\n🔢 Layer Distribution:")
layer_counts = top20['layer'].value_counts().sort_index()
for layer, count in layer_counts.items():
    print(f"   Layer {layer:2d}: {count} heads")

print(f"\n📉 MNR Statistics:")
print(f"   Min:  {top20['mnr'].min():.5f}")
print(f"   Max:  {top20['mnr'].max():.5f}")
print(f"   Mean: {top20['mnr'].mean():.5f}")
print(f"   Std:  {top20['mnr'].std():.5f}")

print(f"\n💡 Key Insights:")
q_ratio = (type_counts.get('Q', 0) / len(top20)) * 100
print(f"   • Query heads dominate: {q_ratio:.0f}% of top 20")
mid_layer_count = len(top20[(top20['layer'] >= 10) & (top20['layer'] <= 18)])
print(f"   • Middle layers (10-18): {mid_layer_count}/20 ({mid_layer_count/20*100:.0f}%)")
print(f"   • Layer 14 is most effective: {layer_counts.get(14, 0)} heads")
print("="*70)
