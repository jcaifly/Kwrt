# 云端前置检查记录（2026-10-11）

本记录是此次云端修改时的检查快照。**配置检查通过；完整固件编译尚未执行；真机验证尚未执行。** 后续 Actions 构建的实际结果以该次运行的日志、`artifact-check.json` 和固件 Artifact 为准。

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
