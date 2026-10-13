# 验证记录

当前阶段：独立 eMMC TAR 构建已完成 make 的编译/镜像生成阶段，
在后续 APK 软件源验收因注释解析错误而失败，未发布通过完整验收的固件。
已修正检查器并重新验证，下一次构建结果以对应 Actions 运行记录为准。
实际 GPT/U-Boot 和真机仍待验证，尚未确认可刷写。
构建附件中的 VALIDATION.md 会依据本次实际镜像检查结果生成；
合成测试、配置检查、镜像检查与真机运行必须分别报告。

## 实际来源与设备证据

- 云端连接 `jcaifly/Kwrt`，默认分支 `25.12`，本任务开始时提交
  `67653046240b4c29faab12e8814102992d88c6d1`；不推送/合并默认分支。
- 独立审核分支 `codex/rax3000m-emmc-openclash`；保留此前 Newifi 和其他设备内容。
- 固定官方稳定 v25.12.5、发行版 feeds 和 OpenClash，见 sources.env。
  官方可见最新 25.12 标签及 releases/latest 为 v25.12.5，维护分支仍存在。
- 用户上传商家镜像确认 `cmcc,rax3000m-emmc`、`PARTLABEL=rootfs` 和
  kernel/rootfs 分开的 TAR；完整静态证据见 VENDOR-FIRMWARE.md。
- 新设备补丁复用共用 DTS，保留官方统一 profile 和正式 NAND/eMMC overlays，
  采用仓库已有的 Kwrt eMMC 身份/路径，无 GPT/引导修改或伪造支持列表。
- 路由器尚未到手，实际 GPT、当前脚本、U-Boot 版本及恢复路径仍待用户采集。

## 实际执行的前置检查

```sh
source /workspace/.kwrt-env/activate.sh
OPENWRT_MAKE=kwrt-make bash scripts/rax3000m-emmc-openclash.sh prepare \
  /workspace/scratch/rax3000m-build-emmc-tar /workspace/scratch/rax3000m-artifacts-emmc-tar
python3 scripts/check-rax3000m.py config OPENWRT_DIR config-check.json
python3 scripts/check-rax3000m.py provenance KWRT_DIR BUILD_ROOT sources.json
python3 -m unittest discover -s scripts/tests -p 'test_check_*.py' -v
actionlint -shellcheck=PATH_TO_SHELLCHECK .github/workflows/rax3000m-emmc-openclash.yml
shellcheck -x scripts/rax3000m-emmc-openclash.sh
shellcheck -s busybox OPENWRT_DIR/target/linux/mediatek/filogic/base-files/lib/upgrade/rax3000m-emmc.sh
```

实际新目录 prepare 退出码 0，包含 `make defconfig` / `make prereq`。
容量 guard 的语法整理后，按精确补丁反向/正向重新应用到同一检查树，
配置及来源检查再次通过。补丁与 Git diff 精确比对，拒绝其他源码更改。
选中唯一 `TARGET_mediatek_filogic_DEVICE_cmcc_rax3000m-emmc`，
232 个构建包、588 条运行依赖，无单独 m 包、排除应用、核心、SDK/ImageBuilder。
这不是最终已安装包数，最终值在编译后按 manifest 和 APK 数据库核对。
最终 .config SHA256：
`ae97adc4ec194cd515d3a19f1edbfde4dfecc180800cadbe81f0ceffea4c031b`。
**这是配置哈希，不是固件哈希。**

21 个本设备回归测试通过，覆盖官方双 overlay 保留、TAR 身份/root 路径、
哈希损坏、特殊文件、越界、错误架构/包/核心，以及实际 shell guard 对
内核、root/初始化标记和配置备份超限的拒绝。容量测试模拟硬件读取，不写设备。
原 Newifi 7 项一同运行，共 28 项通过。
11 个真实配置负例均被拒绝：第二设备、全设备、SDK、DNS 冲突、缺无线/IPv6、
额外应用/核心、关闭签名、错误 feed 和错误架构；原配置恢复后通过。
商家镜像通过实际 TAR/FIT/SquashFS/ARM64 校验，并只读解析升级脚本文本。

actionlint 1.7.11、ShellCheck 0.10.0、bash/sh 及 Python 语法检查通过。
原生 BusyBox ash 支持 local，guard 的 ShellCheck 使用 busybox 模式。
OpenClash 的 host 依赖及 APK 更新校验补丁通过，核心上传/更新脚本保持原生。
固定 mt76 `39c960c3ada558b4c2e7915772483d3731573d09` 的 `wed_enable` 默认 false；
内核 WED 支持保留，不新增启用参数，防火墙两种 flow offloading 默认关闭。

独立 eMMC profile 无固定 IMAGE_SIZE。实际 kernel/rootfs 分区上限、合理可写空间和
首次升级的旧脚本行为待实机证据；不把此前统一 profile 的 512 MiB 上限套到此路径。
最终镜像检查包含 TAR/FIT/元数据/尺寸、manifest/APK 数据库、ARM64 ELF、真实
内核 ABI、中文资源、无核心及安全默认值；失败时保留日志，不发布未通过的候选。

## 状态区分

| 项目 | 状态 / 证据 |
| --- | --- |
| 源码及商家镜像路径分析 | 已完成，固定源码和上传文件 |
| 新 `.bin` 配置检查 | 通过，真实 defconfig/prereq、588 条依赖及 11 负例 |
| 工作流及回归检查 | 修复后通过，29 项本设备测试，连同原测试共 36 项 |
| 新 `.bin` 编译/镜像生成 | 38268273643 的 make 阶段完成；后续软件源验收失败，整次运行失败 |
| 新镜像完整验收/最终交付 | 未完成，未发布通过验收的固件；不得把商家 SHA256 当成新固件哈希 |
| 当前系统预检查 | 待验证；未执行 sysupgrade -T |
| 引导/GPT/恢复兼容性 | 待验证，尚未确认可刷写 |
| 双频、网口、上网、USB、重启、配置保留、24～48h | 待真机验证 |
| 手动安装 ARM64 核心、导入配置后的代理及停用恢复 | 待验证，未安装 Mihomo |

新的独立 eMMC TAR 验证构建：
[38268273643](https://github.com/jcaifly/Kwrt/actions/runs/38268273643)，
实际代码提交 `3de52f8c16370da6ac32d5072cd7184360314d62`。
依赖安装、21 项本设备测试、配置准备通过，make 完成至 checksum。
运行在北京时间 2026-10-13 02:25 于软件源验收失败，错误 `Unexpected APK feed`。
诊断附件 `rax3000m-emmc-openclash-diagnostics-38268273643` 上传成功并保留。
公开错误注释及脚本执行顺序表明失败发生在 APK 源检查；尚无可交付镜像及 SHA256。

错误来自本检查器将官方 `customfeeds.list` 的注释示例
`# http://www.example.com/path/to/files/packages.adb` 视为启用源。
修复仅在解析时忽略空行/完整注释，实际源仍严格核对 HTTPS 官方 25.12.5、
target/架构和不存在的 OpenClash feed，并要求存在实际启用源。
报告同时保留原始源文件文本和启用源列表，错误带文件名与行号。
签名、包依赖和内核 ABI 检查均未放宽。

通过固定源码的 `FeedSourcesAppendAPK` 和 `VERSION_SED_SCRIPT` 实际生成四个官方源，
再复制固定 APK 软件包的原始 customfeeds.list，复现旧检查器拒绝注释示例，
修复后通过；去掉同一示例的注释后仍拒绝。
新增 8 项回归测试覆盖注释/空白、启用非法源、错误发行版/架构、虚构 feed、
只含注释的空源和非法活动行。36 项整体测试、配置/来源和 workflow 语法检查通过。
未触碰设备、内核、软件包选择、分区和引导逻辑。

修复提交 `69a0deb88550dff98882d493343243959ae73920` 已推送审核分支。
新的验证运行：[38336069750](https://github.com/jcaifly/Kwrt/actions/runs/38336069750)。
已观察到依赖安装、29 项本设备测试和最终配置准备通过，正在重新完整编译。
完整镜像验收及交付仍以该运行的最终结果为准，默认分支未修改。

此前运行 [38260284023](https://github.com/jcaifly/Kwrt/actions/runs/38260284023)
使用统一 cmcc_rax3000m `.itb` 路径，是收到商家文件前的验证构建，
**不作为这台独立 kernel/rootfs 设备的升级交付**。保留其日志，不改名冒充 `.bin`。

本地商家文件检查记录在 `/workspace/scratch/rax3000m-vendor-firmware/`，
新配置/来源报告在 `/workspace/scratch/rax3000m-artifacts-emmc-tar/diagnostics/`。
GitHub API 在云端返回 Forbidden；HTTPS Git 功能及公开运行页面可用。
不要求用户向聊天发送 Token，不假称可读取需要登录的 Actions 附件。
无手动入口时由用户审核并决定是否让工作流进入默认分支，本任务不代为合入。
