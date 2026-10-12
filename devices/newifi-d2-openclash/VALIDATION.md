# 云端前置检查记录（2026-10-11）

以下前置检查是首次推送之前的历史快照。**当时配置检查通过；完整固件编译尚未执行；真机验证尚未执行。** 首次 Actions 构建及后续修复见文末；实际构建结果以对应运行的日志、`artifact-check.json` 和固件 Artifact 为准。

## 仓库和修改范围

当前连接仓库为 `jcaifly/Kwrt`，起始提交 `d59e8be835f5a6ff9bfc2034ca14184c4b89b916`。只读查询确认它与请求中的 `kiddin9/Kwrt` 的 `25.12` 分支提交一致。已阅读原有两份工作流、公共和 MT7621 配置/DIY 脚本、Newifi D2 的设备/DTS/网口定义，以及实际使用的 OpenClash 包源码。

本次仅新增独立工作流、设备配置、源码锁定文件、包宿主依赖补丁、默认停用脚本、检查/构建脚本和说明。原有已跟踪文件、其他设备、现有构建流程不作修改。未推送、未合并、未刷机、未访问用户电脑或路由器。

## 实际执行与结果

| 检查 | 结果 |
| --- | --- |
| `actionlint 1.7.11`（同时调用 ShellCheck） | 通过；只检查新增工作流 |
| `shellcheck 0.10.0 -x`、`bash -n`、`sh -n`、Python 语法检查 | 通过 |
| 在新构建目录执行完整 `prepare` | 通过，退出码 `0` |
| 固定提交检出、OpenClash 稀疏检出、零 fuzz 应用包补丁 | 通过；没有获取插件以外的独有 feed blob |
| `make RECURSIVE_DEP_IS_ERROR=1 defconfig` | 通过；未出现循环依赖错误 |
| `make prereq` | 通过，ramips/mt7621 |
| 最终 profile/架构 | 唯一 `DEVICE_d-team_newifi-d2` / `mipsel_24kc` |
| 全设备、全包、全 kmod、SDK、ImageBuilder、其他 rootfs 格式 | 全部关闭 |
| 最终配置的软件包及依赖 | 199 个选中包，核对 528 条启用的运行依赖；无额外 `=m` 软件包 |
| dnsmasq / 防火墙冲突 | `dnsmasq-full` + nftset + firewall4；旧变体未选中 |
| OpenClash | `0.47.156-8`；APK 元数据版本 `0.47.156-r8` |
| Mihomo / 其他代理插件 / Docker | 未选中；插件源文件无内核载荷，构建配方不下载内核 |
| 设备分区、镜像限制、双频及五个网口定义 | 与锁定的上游源码相同；未修改 |
| 合成错误输入检查 | 14 项均正确拒绝，测试临时配置/镜像已恢复或删除 |
| GitHub Actions 完整编译 | 未执行：GitHub API 返回 `Forbidden`，无法确认写入或触发权限 |
| 最终 BIN、SHA256、最终包清单、实际体积 | 尚未产生；会在完整构建成功后检查并保存 |
| 真机 Wi-Fi、WAN/LAN、联网和稳定性 | 未验证，须刷机后测试 |

负向检查覆盖：额外设备、SDK 开启、全包选择、dnsmasq 冲突、旧防火墙冲突、缺少 OpenClash、缺少 Ruby/YAML、缺少传递依赖 ruby-psych、把 Mihomo 选作单独编译包、额外代理应用、缺失镜像、错误镜像型号、超限镜像及预置内核路径。这些输入是检查器测试数据，不是真实固件；没有下载或编译 Mihomo。

最终配置 SHA256：`d2ce447d12e96dc68afce9b7be91fcbb3e74bd79dcbdbd518918bc55994bc845`。这只是配置文件校验值，**不是固件校验值**。完整配置、选中包列表、依赖报告、提交记录和准备日志保存在本云工作区的 `/workspace/scratch/newifi-d2-artifacts-checked/diagnostics/`，负向检查报告在 `/workspace/scratch/newifi-negative-checks/summary.json`；交付包同时保存这些证据。

准备阶段会对未导入的可选软件包打印 `libpam`、`libtirpc`、`libev`、`libnetsnmp` 等元数据警告。相关选项/软件包未在本配置中启用；最终选中包的条件依赖检查通过。这不代表全 feed 适用，实际编译仍需完成。所有失败/诊断日志保留，没有忽略启用包的依赖。

准备流程曾发现 feeds 刷新会丢弃当时未导入的 OpenClash/中文选项；已修复为导入完成后重新应用设备配置，再运行 defconfig。另修正了来源检查器对 Curl 运行依赖、共享 Git blob 的误判，随后从新的构建目录重新执行准备流程并通过。

## 体积和后续验收

设备物理闪存为标准 32 MiB，固件分区及设备镜像上限为 **33,226,752 字节（32448 KiB）**。没有真实 BIN 时不能报告实际大小或剩余空间。构建后的检查器核对文件实际大小、profiles.json、固件内嵌型号/目标信息、最终包名称/版本、组装 rootfs 包数据库以及内核文件缺席情况；任何一项失败都不发布固件 Artifact。

剩余可写空间只能在真机上测量；报告中的镜像余量不等于 overlay 可用容量。该固件保留必要驱动和网络功能，若超过限制，应保留日志说明体积来源并另行讨论方案，不扩大分区或擅自删除基础功能。

## 首次 Actions 构建失败与修复（2026-10-12）

运行 [38152175493](https://github.com/jcaifly/Kwrt/actions/runs/38152175493) 使用 Kwrt 提交 `6ed5918033faaa5183202a7d0cc08d01c8c79833`。来源准备和最终配置检查通过；用户提供的完整末尾日志显示 `make` 已完成工具链、内核、包编译、镜像安装、包索引和校验步骤，随后配置及来源检查再次通过。产物检查失败于 `Missing final APK package database`，固件上传被跳过，诊断 ZIP 保存成功。

根因是检查器把 `STAGING_DIR_ROOT`（`staging_dir/target-*/root-ramips`，软件包暂存目录）当成已安装的最终根文件系统。锁定的上游 `rules.mk` 定义 `TARGET_DIR=$(BUILD_DIR)/root-$(BOARD)`；`package/Makefile` 在该目录执行 APK 安装及根文件系统 overlay 合并。实际数据库位于 `build_dir/target-*/root-ramips/lib/apk/db/installed`。APK 3.0.2 的数据库文件名和文本格式正确，错的是根目录。

已修正为检查最终 `build_dir` 根文件系统，并在成功报告中记录 rootfs 和数据库的相对路径。数据库必须存在且包名/版本与最终 manifest 完全一致；原有镜像大小、型号、依赖、Mihomo 缺席及默认停用检查继续执行。

实际执行 `python3 -B -m unittest discover -s scripts/tests -v`，7 项回归检查通过。测试构造有效最终 rootfs 及无数据库的暂存目录；旧提交的检查器复现相同报错，修复后通过。负向检查仍拒绝用暂存数据库替代缺失的最终数据库、包版本不一致、最终 rootfs 中的内核文件、默认启用代理、自动下载脚本及多个最终 rootfs。原有 14 项负向检查再次通过；新增工作流通过 actionlint/ShellCheck，Python 及 Summary 语法检查通过，Summary 渲染使用合成数据检查通过。测试使用合成输入和模拟的 fwtool 解码，不代表真实镜像验收，没有获取或执行 Mihomo。

工作流增加回归检查和成功后的 Summary，保留 `workflow_dispatch`；仅独立验证分支 `codex/newifi-d2-openclash-verify` 可通过本任务文件的 push 触发一次单设备验证。标准公开仓库 runner、设备配置、源码锁定提交和闪存分区保持原设置。修复后的真实构建及最终体积/SHA256 仍需对应新运行完成后确认；真机功能仍待验证。

## 修复后的真实构建结果（2026-10-12）

验证运行 [38194072912](https://github.com/jcaifly/Kwrt/actions/runs/38194072912) 已成功，于北京时间 2026-10-12 11:13 结束，耗时约 1 小时 13 分钟。回归测试、源码/配置准备、完整编译及产物验收、固件上传、Summary 发布和诊断上传全部成功。前一次 APK 数据库路径误判已修复。

实际构建的 Kwrt 提交为 `082f7c331aeea8849d6a16f4a6d3a761e89a9f77`；修复实现位于 `0c9857083fc8840b4d66f75cf21b90706c5a1fea`，验证提交仅额外增加工作流触发范围的说明注释。来源检查确认 OpenWrt `4da53efc2fe744601e6189492dbd06b8930d72b8`、packages `506c37591d7cd9b3cfd812e69e708349268f9865`、LuCI `27a9c0c94264063894d40420956696d19b175744` 和 OpenClash feed `5ce75c9f2b084c7e3767c630985bb43819f16fbc`。OpenClash 最终 APK 版本为 `0.47.156-r8`。

工作流验收确认唯一 Newifi D2 squashfs sysupgrade 镜像、型号/目标及校验元数据匹配、大小不超过 **33,226,752 字节**、必要包齐全且最终 manifest 与实际 APK 数据库的包名/版本完全一致、没有预装 Mihomo 内核及其他代理应用、默认代理停用及没有首次开机自动下载脚本。真机双频 Wi-Fi、全部网口、联网和负载稳定性仍未验证。

已上传并保留 30 天：

- [固件及最终配置/包清单/来源/验收报告 ZIP](https://github.com/jcaifly/Kwrt/actions/runs/38194072912/artifacts/11723838795)：`newifi-d2-openclash-firmware-38194072912`。
- [构建与诊断日志 ZIP](https://github.com/jcaifly/Kwrt/actions/runs/38194072912/artifacts/11724122926)：`newifi-d2-openclash-diagnostics-38194072912`。

公共页面显示固件下载 ZIP 为 17.7 MB；该值及 Artifact digest 属于压缩下载包，不能当作 BIN 的精确大小或 SHA256。精确 BIN 大小与上限见固件包中的 `artifact-check.json`，BIN 校验值见 `SHA256SUMS`；`final.config`、`packages.manifest` 和 `sources.json` 保存对应实际构建数据。当前云环境不能读取需登录的附件，尚未在云端独立下载并复核 BIN。剩余 overlay 空间仍需真机测量。
