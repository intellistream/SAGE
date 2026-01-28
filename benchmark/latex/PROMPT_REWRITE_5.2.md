# Prompt: 改写 5.2 Node Scalability 小节

## 任务

请根据以下**修正后的实验数据**改写 5.2 小节。保持学术论文风格，确保数据准确。

## 修正后的数据（保留两位小数）

| Pipeline | 1 Node | 2 Nodes | 4 Nodes | 8 Nodes | 16 Nodes | Speedup |
|----------|--------|---------|---------|---------|----------|---------|
| Compute  | 38.14  | 55.03   | 57.16   | 38.90   | 19.39    | **0.5×** |
| RAG      | 1.55   | 3.03    | 5.84    | 11.41   | 17.60    | **11.4×** |
| Mixed    | 1.64   | 3.16    | 4.71    | 4.51    | 10.04    | **6.1×** |

### 关键发现

1. **RAG 实现近线性扩展** (11.4×/16 = 71% 效率)
2. **Mixed 展现中等扩展性** (6.1×/16 = 38% 效率)，8 节点处有性能下降 (4.51 < 4.71)
3. **Compute 出现扩展性反转** - 4 节点后吞吐量反而下降，16 节点比单节点还低

### 扩展性反转的解释

Compute pipeline 的反转现象有两个原因：

1. **任务粒度过细**：Compute 任务仅 ~25ms，远低于推荐的 100ms 阈值。当节点增多时，分布式协调开销（Ray actor 调度、数据序列化）占比增大。

2. **Amdahl 定律**：设串行部分（调度开销）为 $s$，并行加速比上限为 $1/(s + (1-s)/N)$。当 $s > 0.5$ 时，增加节点反而降低吞吐量。

## 写作要求

1. **只保留图，不要表格** - 图和表内容重复，只需 Figure~\ref{fig:node_scalability}
2. **更新 caption** - 反映 RAG 11.4× 和 Compute 0.5× 的结果
3. **诚实报告异常** - Compute 的扩展性反转和 Mixed 8 节点下降是真实现象，需解释而非隐藏
4. **保持 insight** - 最后的洞察段落应保留，强调任务粒度 >100ms 的建议

## 参考代码框架

```tex
% ---------------------------------------------------------------------------
\subsection{Node Scalability}
\label{subsec:eval_scalability}
% ---------------------------------------------------------------------------

We investigate how SAGE scales with cluster size by measuring throughput as 
nodes increase from 1 to 16. Figure~\ref{fig:node_scalability} presents 
results for all three pipeline types.

\begin{figure}[t]
\centering
\includegraphics[width=0.95\linewidth]{Figures/Experiment/node_scalability.pdf}
\caption{Node scalability across pipeline types. RAG achieves 11.4$\times$ 
speedup at 16 nodes (71\% efficiency). Compute exhibits \textit{scalability 
inversion}---throughput peaks at 4 nodes then declines due to coordination 
overhead exceeding task duration.}
\label{fig:node_scalability}
\end{figure}

% [Table commented out - Figure already shows the same data]
% \begin{table}[t]
% ... original table ...
% \end{table}

The results reveal distinct scaling behaviors across pipeline types:

\paragraph{RAG achieves near-linear scaling.}
[描述 RAG 的 11.4× 加速比，71% 并行效率]

\paragraph{Compute exhibits scalability inversion.}
[描述 Compute 从 4 节点后吞吐量下降的现象，解释任务粒度过细导致的问题]

\paragraph{Mixed workloads show moderate scaling with anomaly.}
[描述 Mixed 的 6.1× 加速比，以及 8 节点处的性能下降]

\textbf{Insight:} [保持任务粒度 >100ms 的建议]
```

## 注意事项

- 加速比定义：`Speedup = Throughput(16 nodes) / Throughput(1 node)`
- 不要发明数据，只使用上表中的数值
- Compute 的 0.5× 加速比意味着 16 节点比单节点更慢，这是真实的实验结果
