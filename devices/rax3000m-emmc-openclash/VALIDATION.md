# 验证记录

当前阶段：商家镜像已做静态检查，独立 eMMC TAR 配置/工作流的前置检查通过。
新的 `.bin` 候选尚未完成完整编译，尚未确认可刷写。
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
| 工作流及回归检查 | 通过，21 项本设备测试，连同原测试共 28 项 |
| 新 `.bin` 完整编译 | 尚未完成，以新 Actions 运行实际状态为准 |
| 新镜像完整性/最终大小/SHA256 | 待实际产物 |
| 当前系统预检查 | 待验证；未执行 sysupgrade -T |
| 引导/GPT/恢复兼容性 | 待验证，尚未确认可刷写 |
| 双频、网口、上网、USB、重启、配置保留、24～48h | 待真机验证 |
| 手动安装 ARM64 核心、导入配置后的代理及停用恢复 | 待验证，未安装 Mihomo |

新的独立 eMMC TAR 验证构建：
[38268273643](https://github.com/jcaifly/Kwrt/actions/runs/38268273643)，
实际代码提交 `3de52f8c16370da6ac32d5072cd7184360314d62`。
已观察到依赖安装、21 项本设备测试、最终单设备配置准备通过，正在完整编译；
此记录尚无新镜像大小或 SHA256，不将商家文件的哈希充当本次候选的哈希。

此前运行 [38260284023](https://github.com/jcaifly/Kwrt/actions/runs/38260284023)
使用统一 cmcc_rax3000m `.itb` 路径，是收到商家文件前的验证构建，
**不作为这台独立 kernel/rootfs 设备的升级交付**。保留其日志，不改名冒充 `.bin`。

本地商家文件检查记录在 `/workspace/scratch/rax3000m-vendor-firmware/`，
新配置/来源报告在 `/workspace/scratch/rax3000m-artifacts-emmc-tar/diagnostics/`。
GitHub API 在云端返回 Forbidden；HTTPS Git 功能及公开运行页面可用。
不要求用户向聊天发送 Token，不假称可读取需要登录的 Actions 附件。
无手动入口时由用户审核并决定是否让工作流进入默认分支，本任务不代为合入。
