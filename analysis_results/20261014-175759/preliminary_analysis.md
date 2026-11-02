# 初步结果分析（报告撰写素材）

实验 ID：`20261014-175759`。以下数值均取三轮中位数；机制性解释属于结合内部指标得到的推断，正式报告还应结合论文或源码引用。

## 1. High workload 的 Recall–Latency 权衡

- PipeANN-Filter 的 L 从 20 增至 80 时，Recall@10 从 81.6% 增至 97.4%，Mean Latency 从 20.13 ms 增至 54.14 ms，Mean I/O 从 101.2 增至 229.6。搜索预算提高带来了更高 Recall，同时增加了延迟和逻辑 I/O。
- GateANN 的 L 从 160 增至 640 时，Recall@10 从 81.3% 增至 98.7%，Mean Latency 从 9.26 ms 增至 41.67 ms，Mean I/O 从 24.66 增至 88.94，呈现相同的质量—开销权衡。
- 在两个较为接近的 Recall 点上：GateANN L=160（81.3%，9.26 ms）与 PipeANN L=20（81.6%，20.13 ms）相比，测得延迟约低 54%；GateANN L=320（93.2%，22.22 ms）与 PipeANN L=40（92.7%，33.43 ms）相比，测得延迟约低 34%。这些比较仅适用于本次同一 ECS 云盘环境。
- 最高预算点的 Recall 并不完全相同：GateANN L=640 为 98.7%，PipeANN L=80 为 97.4%，因此不能把 41.67 ms 与 54.14 ms 直接表述成严格同等质量下的加速比。

## 2. Selectivity 敏感性

- GateANN 固定 L=320 时，从 Low 到 High，Recall@10 由 34.3% 升至 93.2%，延迟由 1.50 ms 升至 22.22 ms，Mean I/O 由 4.38 升至 46.75。Low 档虽然最快，但 Recall 明显下降，不能只根据延迟判定性能更好。
- 同时，GateANN 的 FilterSkips 从 Low 的 320.72 降至 High 的 280.24，而 Tunnel time 仅由 558 us 变为 603 us。数据表明更强过滤时更多候选在 I/O 前被跳过，并伴随更少 I/O 和更低延迟；但低 Selectivity 下的可达性或搜索充分性可能受限，需结合 Pre-I/O Filtering 与 Graph Tunneling 机制进一步论证 Recall 下降原因。
- PipeANN-Filter 固定 L=40 时，Low 档 Recall 为 98.6%、延迟 17.42 ms、Mean I/O 80.0，并且 200 条查询全部走 Pre-filter；Medium 和 High 的 200 条查询全部走 In-filter。该执行路径切换与性能的非单调变化同时出现。
- PipeANN-Filter 的 Medium 比 High 更慢（41.28 ms 对 33.43 ms），Mean I/O 也更高（181.5 对 141.6），过滤假阳性指标为 27.0 对 12.5。这组内部证据可用于提出“Medium 标签分布或 In-filter 候选处理造成额外开销”的假设，但真实标签分桶并非严格单变量实验，不能把差异全部归因于 Selectivity。

## 3. 资源权衡

- PipeANN-Filter 正式索引为 8.425 GiB，GateANN 为 0.475 GiB；本次课程预构建索引中前者约为后者的 17.7 倍。
- PipeANN-Filter 查询峰值 RSS 约 135.9 MiB，GateANN 约 404.4 MiB；后者约为前者的 3.0 倍。GateANN 日志显示加载了 49 MB 的 SpmatFilterStore 和约 0.123 GB 的 FullAdjIndex，但 `peak_rss_kb` 是整个查询子进程峰值，不能把全部 RSS 差值归因于这两个结构。
- 本次结果体现出 SSD 空间与 DRAM 使用方式明显不同：PipeANN-Filter 使用更大的磁盘索引而查询 RSS 较低，GateANN 使用较小的磁盘索引但查询 RSS 较高。正式报告应把这一资源差异与相近 Recall 下的延迟结果一起讨论。

## 4. 报告表述限制

- `mean_ios` 是各系统内部逻辑 I/O；两套系统的 I/O 页面大小和统计实现不同，不能根据绝对值直接宣称某系统物理 I/O 更少。
- Low、Medium、High 使用不同真实标签，标签频率、候选分布和查询难度可能同时变化。
- ECS 使用 ESSD Entry 云盘，不是本地直连 NVMe SSD；绝对延迟不应外推到其他硬件。
- 每个配置仅有 200 条查询和三轮重复，报告应展示最小值—最大值并说明潜在云主机后台波动。
