# 阿里云 ECS 实验继续操作记录

更新日期：2026-10-14。此记录接续本目录中的两份 Windows/WSL2 说明；后续实验使用阿里云服务器，不再在本机安装 WSL2。

当前进度：数据集校验、两套系统编译、Debug 索引构建及正确性检查、两套正式预构建索引获取与校验、正式实验均已完成。正式实验 ID 为 `20261014-175759`，课程脚本已收集并验证 30 行结果。`course_runs` 已下载到本地备份，正式结果、环境信息和逐次日志齐全。已完成三轮汇总、6 张矢量图和完整 Markdown 报告初稿；下一步为填写个人信息、人工复核、按 Word 参考样式排版并导出 PDF。现有结果已满足课程正式实验要求，无需为凑数据重复运行；优化补充实验仅在确有研究需要时开展。确认最终 PDF 和本地备份无误前不要释放 ECS。

## 实验目标与环境决策

完成课程仓库中的 PipeANN-Filter 与 GateANN 对比实验，最后提交报告 PDF，并保留原始 CSV、环境信息、命令和日志。

课程仓库：https://gitee.com/wei-fangyu/fvs-course-lab

服务器已创建，课程接受云服务器。本机 SSD 仅剩约 10 GB，F 盘是 HDD，因此数据、索引、编译及性能测试全部在云服务器完成；本机可保存报告和实验结果备份。

课程要求两套系统在同一台机器、同一 SSD 存储环境下运行。当前使用同一块 ESSD Entry 系统盘；报告中需明确标注为云盘，而不是本地直连 NVMe SSD。

## 已确认的服务器与仓库信息

- ECS 实例 ID：`i-bp1c8j1ow4dhqu0z2iyh`，地域：杭州 `cn-hangzhou`。
- 控制台：https://ecs.console.aliyun.com/server/i-bp1c8j1ow4dhqu0z2iyh/detail?regionId=cn-hangzhou&change=true
- 选择配置：通用算力型 u1，4 vCPU、8 GiB，ESSD Entry 40 GiB，1 台。
- 登录用户：`root`。
- 架构：`x86_64`；`nproc` 输出为 `4`。
- 内存：系统显示总计 7.3 GiB，检查时 available 为 6.7 GiB。
- Swap：0，不为性能测试预先增加 swap。
- 系统盘：`/dev/vda3`，ext4，挂载 `/`；检查时 40G 总容量、35G 可用。
- apt 软件源为 Ubuntu jammy（22.04）系列；下次可用 `cat /etc/os-release`补充确认版本。
- 云端课程目录：`/root/fvs-course-lab`，即 root 用户的 `~/fvs-course-lab`。
- 云端仓库 Commit：`e44eab5d1b040ffdebc80374a13b304a9c4d37de`。
- 助手已将课程仓库下载至本地 `course-repo/` 阅读；这是本地参考副本，不是云端实验工作目录。

16 GiB 是课程建议配置，不是硬性门槛。课程系统准备说明指出 GateANN 正式查询通常远低于 1 GiB RSS，且正式索引无需自行构建。8 GiB 可继续尝试，但要观察编译与 Debug 构建的内存情况。

## 已完成与当前运行位置

1. 已连接云服务器并完成 CPU、内存、磁盘检查。
2. 已成功执行 `apt update`。
3. 已克隆课程仓库，并确认上述 Commit。
4. 首次安装依赖的长命令粘贴不完整，出现 `Unable to locate package libgoogle-perftools`。正确包名为 `libgoogle-perftools-dev`，随后提供了短命令分批安装。
5. 数据集下载最终完成，执行 `bash scripts/check_dataset.sh` 后输出 `Dataset verification passed: /root/fvs-course-lab/datasets/yfcc_course_v1`。
6. 数据集校验后的磁盘检查：`/dev/vda3` 总容量 40G、已用 4.0G、可用 34G、使用率 11%。这是当时的快照，不是当前索引下载后的空间。
7. 用户确认 PipeANN、GateANN 均完成编译。按指导使用 `FVS_BUILD_JOBS=2` 顺序编译；完整 PipeANN 编译输出未贴出，后续 Debug 检查已证明其程序可运行。
8. GateANN 编译检查输出：目标 `search_disk_index_yfcc` 达到 100%；expected/actual commit 均为 `71e87cbf0e25c0400c0109dd25a64a7c4dccc9dd`；两个二进制检查通过；`CMAKE_BUILD_TYPE=Release`、`USE_AIO=ON`，最终 `DOCTOR PASS`。
9. 两套 Debug 索引已构建并通过正确性检查，详见下节。构建指导为依次运行、`--threads 2`。
10. 首次正式索引下载在 PipeANN 压缩包约 50.0 MiB（总计约 1068 MiB）处再次出现 `curl: (92) HTTP/2 stream 0 was not closed cleanly: PROTOCOL_ERROR (err 1)`，当时平均速度约 19 KiB/s、已耗时约 45 分 50 秒，下载命令已退出，没有并行启动第二个下载。
11. 因 GitHub Release 下载过慢且反复中断，改用课程仓库公布的夸克网盘备用源，手动取得 `pipeann_yfcc_course_1m_index_v1.tar.zst` 和 `gateann_yfcc_course_1m_index_v1.tar.zst`，放入服务器 `/root/fvs-course-lab/course_runs/indices/downloads/`，保持原文件名并交由课程脚本校验、解压和安装。
12. `bash scripts/download_indexes.sh` 已完成，末尾输出 `Both formal indexes are ready under: /root/fvs-course-lab/course_runs/indices`。
13. `bash scripts/check_indexes.sh` 已通过：PipeANN 与 GateANN 的 `manifest.json` 均为 `Manifest OK`，两套正式索引均输出 `Index verification passed`。正式索引位置分别为 `course_runs/indices/pipeann/formal_1000000` 和 `course_runs/indices/gateann/formal_1000000`。
14. `bash scripts/run_formal_experiments.sh` 已成功完成。实验 ID 为 `20261014-175759`；末尾输出 `Collected and validated 30 rows`、`Formal experiments complete`。聚合结果为 `course_runs/experiments/20261014-175759/results.csv`，环境信息为同目录 `environment.txt`。
15. 已补充保存 `system_info.txt`，并将服务器 `course_runs` 下载到本地根目录。已确认本地聚合 CSV 恰好 30 行（PipeANN 15 行、GateANN 15 行），`environment.txt`、`system_info.txt` 以及各轮 `results.csv`、`command.json`、`run.log` 均存在。
16. 已生成本地分析产物：`analysis_results/20261014-175759/summary_by_system_bucket_L.csv`、6 张 SVG 图、`report_tables.md`、`preliminary_analysis.md` 和 `完整实验报告.md`。汇总按 `system + bucket + L` 分为 10 组，每组恰好 3 轮，使用中位数及最小值—最大值范围。报告包含两张必做图，以及 GateANN 时间分解、过滤机制指标、资源权衡和三轮稳定性图；还包含实验问题记录、有效性威胁、证据索引、优化方向和验证计划。

依赖已足以支持两套系统编译、Debug 验证和正式实验；未单独保存全部 apt 安装成功输出。服务器实验与本地备份均已完成，下一阶段只需复核图表、结合论文或源码完成机制与瓶颈论证、提出优化及验证计划，并排版提交 PDF。

## Debug 验证证据（已完成）

执行命令：`bash scripts/run_debug_validation.sh`。

运行标识：`debug-check-20261014-122107`（由日志提供，保留原值）。

```text
PASS pipeann: 200 queries, L=40, Recall@10=96.70%
PASS gateann: 200 queries, L=320, Recall@10=95.20%
DEBUG CORRECTNESS CHECK PASS
Debug validation artifacts: /root/fvs-course-lab/course_runs/results/*/debug_100000/high/debug-check-20261014-122107
```

GateANN 额外日志：Debug base 为 `100000 x 192 uint8`；SpmatFilterStore 含 100000 节点、1087574 标签，约 4.9 MB；FullAdjIndex 使用 `max_nbrs=32`，保存为 `course_runs/indices/gateann/debug_100000/yfcc.full_adj.R32`，日志大小为 0.0122935 GB。

GateANN 本次 High Debug 查询输出：L=320、QPS=70、Recall@10=0.9520、MeanIOs=41.90。这些只作为调试阶段记录，不作为正式性能比较结论；正式报告性能图应使用后续正式实验 CSV。

## 已遇到的问题与处理（供报告使用）

### 依赖包名与长命令粘贴

首次依赖安装出现 `Unable to locate package libgoogle-perftools`。实际所需包名是 `libgoogle-perftools-dev`。改为分批短命令安装，避免长命令粘贴不完整；随后编译和 Debug 验证通过。

### GitHub 下载缓慢及 HTTP/2 中断

数据压缩包约 217 MiB，首次下载到约 90 MiB（41%）后报错：

```text
curl: (92) HTTP/2 stream 0 was not closed cleanly: PROTOCOL_ERROR (err 1)
```

当时运行数据校验报 `checksums file not found`，说明数据尚未完整解压，不能进入实验。重跑 `download_dataset.sh` 后脚本报告压缩包校验失败并自动续传，这是不完整压缩包的预期处理，不应直接认定最终数据损坏。

已观察到续传起点 `94371840` 字节（90 MiB）及后续 `124727296` 字节；下载过程中存在长时间接收量为 0 的情况，也出现约数十 KiB/s 的慢速传输。上传列为 0 属正常下载行为。最终数据集 SHA-256 校验通过，问题已解决；没有足够证据将慢速归因于某个具体网络环节。

曾提供 `curl --http1.1 --fail --location --continue-at -` 作为绕过 HTTP/2 错误的备选方案，但用户未确认执行，因此不记录为实际采用的解决措施。

正式 PipeANN 索引压缩包下载时，同类 HTTP/2 错误再次出现：约 45 分 50 秒仅下载约 50.0 MiB，速度过慢且连接中断。实际采用的处理是停止该次下载，改用课程官方说明中的夸克网盘备用源手动取得两套正式索引压缩包，再让原课程脚本执行 SHA-256 校验、解压和安装。最终 `download_indexes.sh` 和 `check_indexes.sh` 均成功，因此备用压缩包及安装后的索引已通过课程校验。夸克分享页不是 curl 直链，不能设置为脚本的下载 URL。

### tmux 重复会话与后台运行

多次执行 `tmux new -s fvs` 报 `duplicate session: fvs`，表示会话已存在，不表示已进入该会话。一次粘贴还将 `tmux new -s fvs` 和 `df -h /` 放在同一行。创建失败后后续命令仍可能在原终端运行，仅凭重复会话报错不能断定下载受到 tmux 保护。

正确处理为恢复现有会话 `tmux attach -t fvs`，确认其中没有另一个下载后再运行任务；通过 **Ctrl+B，松开后按 D** 分离。用户最新已确认看到 `detached`。此前仅凭输出断言下载一定处于普通终端并不充分；今后以实际会话状态为准。

### 终端方向键字符

进度输出中多次出现 `^[[A`、`^[[B`，对应上、下方向键的转义序列，不是下载错误，也不代表压缩包内容被修改。下载过程中避免用方向键滚动，使用终端滚动条查看历史输出。

## 当前正式实验运行与离开说明

正式实验已经在 `fvs` tmux 会话中启动。运行期间不要按 `Ctrl+C`，不要关闭、停止或释放 ECS 实例，也不要同时下载、编译或运行其他高负载任务。

需要离开网页终端时，按 **Ctrl+B，松开后按 D** 分离 tmux；这只会将会话留在后台运行，不会终止实验。重新连接后执行 `tmux attach -t fvs` 查看进度。正式实验脚本不支持中途续跑，因此不要重复启动第二个正式实验。

本机可以关机，云服务器独立运行。免费额度会持续消耗：当前显示约 0.731 元/小时、约 410 小时只是初始估算。不要增加数据盘或随意变更规格；试用到期或额度耗尽后可能收费。完成后先下载原始结果，再释放资源。

## 下次继续：确认正式实验结果

以下命令均在服务器 Linux 终端执行，不在本机 PowerShell 执行。

```bash
tmux ls
```

若显示 `fvs` 会话，恢复它：

```bash
tmux attach -t fvs
```

若正式实验仍在输出或运行，继续等待，不要同时启动第二个实验。若已返回命令提示符且没有报错，先记录末尾完整输出和 experiment-id，再执行：

```bash
cd ~/fvs-course-lab
df -h /
free -h
ls -lah course_runs/experiments/
```

根据脚本输出定位最新的 `course_runs/experiments/<experiment-id>/`，确认其中至少保留 `results.csv` 和 `environment.txt`；还要保留 `course_runs/results/` 下各次运行对应的 `results.csv`、`command.json` 和 `run.log`。预期正式汇总共有 30 行结果。若脚本报错或中途退出，保留完整输出和已有目录，不要覆盖旧结果；分析原因后使用新的 experiment-id 完整重跑。

数据集已通过校验，无需重新下载。若需复核可执行 `bash scripts/check_dataset.sh`。下面的依赖命令仅保留为历史与重建环境参考，当前无需再次安装。

如依赖尚未安装成功，逐条执行以下短命令（重复执行会保留已安装软件）：

```bash
sudo apt install -y build-essential cmake git curl zstd
sudo apt install -y libaio-dev libgoogle-perftools-dev
sudo apt install -y libopenblas-dev libeigen3-dev
sudo apt install -y python3 time tmux
```

## 实验流程与已执行命令留档

步骤 1—4 已完成，保留命令供报告和复现使用，当前正在执行步骤 5；步骤 6 尚未完成。

每一步成功后再进行下一步，遇到错误保留完整输出，不跳过校验。

### 1. 编译两套系统

在仓库根目录、tmux 会话中执行。8 GiB 内存先使用 2 个编译任务，不用脚本默认的 8 个：

```bash
cd ~/fvs-course-lab
FVS_BUILD_JOBS=2 bash scripts/prepare_pipeann.sh
FVS_BUILD_JOBS=2 bash scripts/prepare_gateann.sh
```

脚本会获取课程固定源码版本，并为 GateANN 应用课程兼容补丁，不要自行替换版本或 backend。若编译因内存不足被杀死，先保存错误，再考虑用 `FVS_BUILD_JOBS=1` 重跑。

### 2. 构建 10 万向量 Debug 索引

两套系统依次执行，构建线程先设为 2。构建线程允许按机器调整，不影响正式查询固定的单线程要求。

```bash
python3 adapters/pipeann_adapter.py build \
  --repo "$PWD/systems/PipeANN" \
  --dataset-root "$PWD/datasets/yfcc_course_v1" \
  --tier debug --run-root "$PWD/course_runs" --threads 2
```

```bash
python3 adapters/gateann_adapter.py build \
  --repo "$PWD/systems/GateANN-public" \
  --dataset-root "$PWD/datasets/yfcc_course_v1" \
  --tier debug --run-root "$PWD/course_runs" --threads 2
```

成功索引已存在时不要盲目覆盖；失败时保留日志，按仓库的重试规则操作。

### 3. Debug 正确性检查

```bash
bash scripts/run_debug_validation.sh
```

必须两套系统均出现 `DEBUG CORRECTNESS CHECK PASS`。检查包含 200 条查询、K/L/线程等参数和 High workload Recall@10 不低于 80%。Debug 数据不用于正式性能分析。

### 4. 下载并校验正式预构建索引

状态：已完成。两套正式索引的 manifest 和内容校验均已通过，无需重新下载或构建。

先检查空间，再执行：

```bash
df -h /
bash scripts/download_indexes.sh
bash scripts/check_indexes.sh
df -h /
```

PipeANN 正式索引解压约 8.43 GiB，压缩包约 1.05 GiB；GateANN 解压约 486 MiB，压缩包约 401 MiB。需考虑数据集、构建目录、压缩包和解压临时空间，不要等磁盘满了再处理。不要重新构建 100 万向量正式索引。

### 5. 正式实验

状态：已完成。实验 ID 为 `20261014-175759`，30 行正式结果已通过课程脚本验证并在本地备份。

保持同一实例、同一云盘；关闭自己启动的无关高负载任务，避免编译或下载同时运行。

```bash
bash scripts/run_formal_experiments.sh
```

保持课程默认参数：Linux AIO、threads=1、beamwidth=8、K=10、mem_L=0、cache budget=0、GateANN FullAdj neighbors=32，重复 3 轮。

High：PipeANN L=20/40/80，GateANN L=160/320/640。Medium、Low：PipeANN L=40，GateANN L=320。最终应汇总 30 行结果。

正式脚本不支持中途续跑；失败后保留旧结果，用新的 experiment-id 重跑，不覆盖原始日志。

### 6. 备份、分析与报告

状态：实验数据备份、统计分析、绘图和完整 Markdown 报告初稿均已完成；最终 Word 排版、个人信息填写、人工复核与 PDF 导出尚待用户完成。

聚合结果：`course_runs/experiments/<experiment-id>/results.csv` 与 `environment.txt`。

单次结果和日志：`course_runs/results/` 下对应的 `results.csv`、`command.json` 和 `run.log`。保留到课程成绩公布，并下载到本机备份后再释放服务器。

按 `docs/结果分析指南.md` 和 `docs/实验报告模板.md` 分析三轮中位数及范围，完成两张图：

1. High workload 的 Recall@10–Mean Latency 曲线。
2. Low/Medium/High 的 Recall、Mean Latency、Mean I/O 三子图。

使用 `mean_latency_us` 而不是 `elapsed_seconds` 绘制查询延迟；`mean_ios` 是系统内部逻辑 I/O，不等同块设备物理 I/O。按相近 Recall 比较系统，不能仅按相同 L 比较。

报告还需包含系统机制、资源权衡、瓶颈证据、优化方向及验证计划；优化代码不要求实现。最终提交 PDF，不需要提交大数据、索引或源码。

本地已完成的报告材料位于 `analysis_results/20261014-175759/`：

- `完整实验报告.md`：严格按最新版模板组织的完整正文，包含环境、系统设计、实验方法、正式结果、机制与瓶颈、优化方向、实验总结、故障记录、有效性威胁和参考文献。
- `figure1_recall_latency_high.svg`：必做 High Recall@10–Mean Latency 图。
- `figure2_selectivity_performance.svg`：必做 Selectivity–Performance 三子图。
- `figure3_gateann_time_breakdown.svg`：GateANN 内部时间分解。
- `figure4_filtering_mechanisms.svg`：PipeANN 路由及 GateANN FilterSkips/Mean I/O。
- `figure5_resource_tradeoff.svg`：索引大小与查询峰值 RSS 权衡。
- `figure6_repeat_stability.svg`：三轮延迟稳定性。
- `summary_by_system_bucket_L.csv`：10 个配置组三轮中位数、最小值和最大值。
- `report_tables.md`、`preliminary_analysis.md`：数据表与分析素材。

本地根目录的 `analyze_formal_results.py` 可从原始正式 CSV 重新生成汇总表和 6 张 SVG 图。报告初稿约 381 行，已纳入论文和固定源码入口；正文明确区分实际测量、机制解释与待验证假设。

现有 30 行正式结果已满足课程要求，不需要为了增加篇幅重复正式实验。报告中的优化部分按课程要求只需提出方案和验证计划，不要求实现；除非教师另行要求或确有研究目的，否则不开展补充实验，避免引入与统一参数不一致的新数据。

## 最终收尾与提交清单

1. 在 `完整实验报告.md` 顶部填写姓名、学号和班级，复核课程或教师是否另有封面字段。
2. 参考 `course-repo/docs/实验报告格式参考.docx` 设置封面、目录、字体、标题、页边距、图表题注和页码；内容要求仍以 `docs/实验报告模板.md` 为准。
3. 将 6 张 SVG 以矢量方式插入或随 Markdown 正确转换，检查图例、误差线、坐标轴、分页和清晰度；至少保证两张必做图完整出现。
4. 人工核对姓名、实验 ID `20261014-175759`、所有表格、图号、参考文献链接和文中交叉引用，不把 Debug 指标当成正式结果。
5. 导出 PDF 后逐页检查：目录、中文字体、公式/代码、表格跨页、SVG 渲染、页码和空白页；最终只提交课程要求的一份 PDF。
6. 至少保留两份本地备份：报告/PDF 与 `course_runs` 原始证据分开存放。保留 `results.csv`、`environment.txt`、`system_info.txt`、`command.json` 和 `run.log` 至课程成绩公布。
7. 确认本地备份可打开、PDF 无误且课程平台提交成功后，才停止或释放 ECS，以免继续消耗免费额度。释放实例前不要误删本地数据；释放云资源通常不可恢复。

如果后续仍需助手协助，应提供最终 PDF 或排版后的 Word/Markdown，用于检查缺页、图表渲染、术语一致性和提交前清单；无需再次提供服务器下载或正式实验输出。

环境信息已保存在 `environment.txt` 和 `system_info.txt`。报告中继续区分已证实结果与推断，不发送密码、私钥或访问密钥。

最新版报告要求不改变实验任务、运行参数或最终提交物。脚本会生成原始结果、环境信息、命令和日志，但不会自动完成报告。正式实验结束后需按最新版 `docs/实验报告模板.md`：整理三轮中位数及波动范围，绘制 High workload 的 Recall@10–Mean Latency 曲线，以及 Low/Medium/High 的 Recall、Mean Latency、Mean I/O 三子图；完成两套系统设计说明与比较、机制和瓶颈分析、资源 trade-off、优化方向及验证计划、实验总结，最后排版并提交 PDF。`docs/实验报告格式参考.docx` 仅供封面、目录和排版参考；若与 Markdown 模板不同，以 `docs/实验报告模板.md` 为准。

截至本次更新，上述报告内容与图表均已写入初稿；剩余工作仅为用户个人信息、人工审阅、排版、PDF 导出与提交。
