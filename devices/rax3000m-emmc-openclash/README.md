# CMCC RAX3000M eMMC / OpenClash 候选固件

本目录是独立构建入口，目标为家庭 100M 宽带、双频 Wi-Fi 和 OpenClash。
设备使用 `mediatek/filogic` / `cmcc_rax3000m-emmc` profile，
匹配用户上传商家固件的真实设备身份及独立 kernel/rootfs 升级路径。
最小设备补丁保留官方共用 DTS、统一 profile 和正式 NAND/eMMC overlays，不伪造设备身份。
本次重制补齐 USB 存储/VFAT 与基础 block-mount 支持，并交付同次构建的签名 APK 仓库。
自动挂载和自动交换区默认关闭；不增加磁盘管理应用或常驻 blockd。
**构建通过的产物仍是候选固件；在当前系统、GPT 和第三方 U-Boot 核对前，尚未确认可刷写。**
本次运行 38336069750 已编译及镜像检查通过，上传 BIN 的 SHA256 与构建记录一致。
实际大小、SHA256、包清单、来源及与商家参考的比较见 [FINAL-IMAGE.md](FINAL-IMAGE.md)。
用户选择 U-Boot 恢复页重刷；旧系统 sysupgrade 的待采集项不参与这条首次写入路线，
需确认的是该恢复页接受格式与写入对象，详见 UPGRADE.md。

用户目前提供的信息：当前系统为 Kwrt，U-Boot 据卖家称来自 yuzhuii，软件分区已调整为约 2GB。
用户更正后的 7 月 15 日商家镜像已确认 Kwrt 25.12-SNAPSHOT / Linux 6.12.94 / `cmcc,rax3000m-emmc` /
`root=PARTLABEL=rootfs rootwait`，详见 [VENDOR-FIRMWARE.md](VENDOR-FIRMWARE.md)。
实际当前版本、U-Boot 版本、GPT 分区边界及引导配置仍待读取；用户暂时无法查看恢复页。
本流程保留现有布局，不因 2GB 容量要求重新分区，也不执行路由器操作。

## 来源与选择

| 组件 | 固定版本 / 提交 |
| --- | --- |
| Kwrt 构建入口 | 当前审核/运行的 Git 提交；实际值写入 `sources.json` |
| OpenWrt | 稳定版 v25.12.5 / `f0a60eee2fe051741c643ea6118718aae1ef17fb` |
| packages | 该发行版 feeds / `5caa62e0bc9f7fb9b0c12a23267bceb7724214dd` |
| LuCI | 该发行版 feeds / `128a7812f4be233c5dd7f7466f534fd888785caf` |
| OpenClash 软件包 | 0.48.002-r9 / kiddin9/op-packages `426eda7eae561e63b6dc78f4c6bcaa4105ca4b16` |
| OpenClash 上游版本标记 | v0.48.002 / `e553e82e01c697aefbe1555261a503f425e00ccd` |
| 必要本地补丁 | 保留 Kwrt eMMC kernel/rootfs 路径；为 APK 单包签名；增加 LuCI host 依赖；移除插件 APK 自更新绕过；补丁哈希写入 `sources.json` |

25.12.5 是准备时官方仓库可见的最新 25.12 稳定标签，使用发行版自带的 feeds 固定值。
Linux 内核及 ABI 使用真实构建结果；不把内核兼容值改成常量，不强装架构或版本不匹配的包。
镜像显示 Kwrt 25.12.5，DISTRIB_DESCRIPTION 含实际 OpenWrt 提交前缀 `f0a60eee2fe0`。
原生 DISTRIB_REVISION / 元数据 revision 为发行版 version 文件的 `r33051-f5dae5ece4`，
完整源码提交以 sources.json 为准，不将原生 release revision 误当成实际 HEAD。
完整实际来源、补丁 SHA256、最终配置及清单均随产物交付。

原仓库通用流程中存在 `CONFIG_SIGNATURE_CHECK=n`、下载失败/校验处理修改、
固定 `.vermagic` 为 `1`、opkg 强制依赖/校验/覆盖补丁、忽略 postinst 失败、
额外应用及无线功率/DFS 修改。
这些设置不能证明兼容性，本设备入口不执行 `devices/common/diy.sh`、
`devices/mediatek_filogic/diy.sh` 或其通用补丁，使用干净上游系统源码。
原有配置和工作流保持原样。
新版仅在本独立构建树增加 APK 单包签名；不会修改仓库其他设备的打包逻辑。

## 包与默认行为

保留基础 Linux 内核、eMMC/MMC、DSA 网口、MT7915/MT7981 双频无线、USB3、
官方校准数据读取及所需 ext4/F2FS 工具，保留原生 DHCP/DNS、IPv4/IPv6、
PPPoE、BusyBox 校时服务、证书、中文 LuCI、HTTPS、SSH 和 APK 包管理。
USB 存储支持常规 USB Mass Storage、VFAT 和内核已有的 ext4，提供基础 block 工具。
不默认挂载外接盘、启用交换区或更改任何 eMMC 分区；用户按需配置外接盘挂载。
LuCI 防火墙及软件包管理页面属于基础管理功能。

额外应用只有 `luci-app-openclash`。其完整声明依赖 `dnsmasq-full`、bash、curl、
ca-bundle、ip-full、ruby、ruby-yaml、TUN、unzip，以及原生 fw4 所需 nftables、
nft TProxy/socket/inet-diag 和 Lua/LuCI 兼容组件均保留。
采用 firewall4/nftables 与 dnsmasq-full 的 nftset 路径，普通 dnsmasq 不同时安装。
不安装其他代理、nlbwmon、ttyd、btop、TurboACC、Docker、SmartDNS、MosDNS 或 AdGuard Home。

- OpenClash 默认 `enable=0`，禁用开机服务；不预置节点、订阅或代理 YAML。
- 小闪存模式默认关闭；核心正常保存在 `/etc/openclash/core/clash_meta`。
- 构建不下载、编译或打包 Mihomo，也没有首次开机下载核心的新增脚本。
- OpenClash 的原生手动上传、核心下载/更新功能保留。用户启用后，它可以按正常机制
  调整 DNS、路由和防火墙；原生启动流程在用户启用且缺少核心时可能尝试下载，
  因此建议先手动安装并验证核心，再启用。
- 防火墙软件/硬件 flow offloading 均设为 0，不添加加速补丁、超频或发射功率修改。
  内核保留上游 WED 支持；固定 mt76 源码的 `wed_enable` 默认为 false，
  不添加启用参数。实际运行状态由真机核对。
- 无周期测速、定时重启或新增长期 debug 服务。基础服务及用户启用后的 OpenClash 可正常运行。
- 使用上游 WAN 输入拒绝策略，不添加 WAN 管理开放规则或额外远程管理服务。

## 构建与下载

工作流：`.github/workflows/rax3000m-emmc-openclash.yml`。
使用 Ubuntu 24.04 普通公共仓库 runner、2 个编译线程，Actions 以提交 SHA 固定，
权限为 `contents: read`，不使用作者私有服务器、个人 Token/密钥或通知服务。
私有仓库会跳过任务，避免擅自消耗付费分钟。

审核分支 `codex/rax3000m-emmc-openclash` 的相关代码推送可以触发一次验证构建，
无需推送或合并默认分支。文档改动不触发该 push 构建。
GitHub 的 `workflow_dispatch` 入口通常要求工作流已存在于默认分支：
如界面尚无手动入口，先由仓库所有者审核变更并决定是否合入；本任务不自动合入或推送默认分支。

手动运行：GitHub 仓库 → Actions → `RAX3000M eMMC OpenClash candidate (no core)` →
Run workflow → 选择包含本配置的分支 → Run workflow。
完成后打开同次运行的 Artifacts：

- `rax3000m-emmc-openclash-candidate-<run_id>`：候选 `sysupgrade.bin`、SHA256SUMS、
  final.config、kernel.config、diff.config、packages.manifest、profiles.json、实际 sources.json、检查 JSON 和说明。
- `rax3000m-emmc-openclash-diagnostics-<run_id>`：prepare/download/编译日志、串行失败诊断（如有）、
  OpenWrt 子任务日志、检查结果、实际上游升级脚本和阶段退出码。失败也保留，默认 30 天。
- `rax3000m-emmc-matching-packages-<run_id>`：同次镜像的签名 APK、签名本地索引、
  公开验证密钥、SHA256SUMS 和验收记录，使用方式见 [PACKAGES.md](PACKAGES.md)。
- Actions Summary 显示实际镜像大小、整包 SHA256、安装包数、内核 ABI 和来源提交。

交付只复制原生 `*cmcc_rax3000m-emmc-squashfs-sysupgrade.bin`。
本独立 profile 不生成 GPT、BL2/preloader 或 FIP/U-Boot；
其他统一 profile 的附带文件**不能作为本次普通升级的刷写对象**。
关闭全设备、全软件包、SDK 和 ImageBuilder；必要工具链及依赖仍照常编译。

云端前置检查可使用已准备的开发工具：

```sh
source /workspace/.kwrt-env/activate.sh
OPENWRT_MAKE=kwrt-make bash scripts/rax3000m-emmc-openclash.sh prepare \
  /workspace/scratch/rax3000m-build-fresh /workspace/scratch/rax3000m-artifacts-fresh
```

普通 Linux 构建机安装工作流列出的依赖后使用原生 make，无需该云端路径。
每次 prepare 使用新的目录，拒绝混入旧源码/产物。
验证失败会终止固件发布，不忽略依赖、架构、内核版本或镜像错误。

## 镜像大小与软件源

Kwrt 的独立 eMMC profile 没有固定 `IMAGE_SIZE`，因为 kernel 和 root 写入不同分区，
实际允许上限必须分别取自现有 GPT，不能用整包大小与“2GB”比较。
`TARGET_ROOTFS_PARTSIZE=448` 保留上游配置值，在这个 TAR profile 中不创建或扩展分区。
构建会报告实际 kernel/root payload 长度及 64 KiB 对齐后的 overlay 偏移；
root 最低所需空间包含 4 KiB 初始化标记，仅证明最低写入范围，不代表可写空间足够。
取得 GPT 后核对真实两个分区容量，并为配置备份、文件系统和日常更新保留合理空间。
新增容量检查按唯一 PARTNAME 找 kernel/rootfs，确认同一 eMMC 并读 sysfs 的 512 字节扇区数，
拒绝 payload/初始化标记/实际配置备份超出分区；升级前和原生 stage2 写入前均执行。
它不写 GPT、引导或 factory，不增加分区尺寸，不忽略现有检查。
旧系统第一次升级仍使用旧系统的脚本，不能据新固件中的保护认定旧系统同样受保护。
报告中的实机容量及 overlay 空间在资料缺失时为空，刷机后仍需 `df -h /overlay` 实测。
不能根据卖家描述或整块 eMMC 总容量推算可写空间。

实际 APK 软件源从最终 rootfs 读取并交付，预期为官方 25.12.5 的
`targets/mediatek/filogic/packages` 及 `packages/aarch64_cortex-a53/{base,packages,luci}`。
本地 source-link OpenClash feed 不在官方服务器发布，因此本设备配置单独关闭
`CONFIG_FEED_openclash` 的软件源条目，插件本身照常编入，不生成一个不存在的下载源。
保留 TLS、APK 签名、包依赖及真实内核 ABI 检查。

自编译内核模块与官方预编译 kmod 的 ABI 不能仅凭相同发行版/内核版本认定相同。
实际内核包完整版本和每个 kmod 的依赖会核对；官方远端 kmod 的匹配状态单独标为未确认。
新版附带经过真实签名验证、包身份比对和离线依赖求解的同次软件包仓库。
它与本次镜像的内核 ABI 和信任密钥匹配，构建私钥不公开，详见 PACKAGES.md。
需要新增内核模块时优先在这个固定来源的工作流一起构建，不能强装、忽略依赖或关闭签名。
系统版本升级采用经过相同兼容性检查的匹配 sysupgrade 镜像，不把全量 `apk upgrade`
当成系统升级或内核 ABI 兼容性证明。
第三方插件自更新的包签名可信性不由本次构建证明；优先通过本工作流更新管理插件。
所选 OpenClash 原始管理插件更新脚本使用 `--allow-untrusted` 和 `--force-overwrite`。
本设备的 `openclash-apk-verification.patch` 去掉这两个参数及日志中的绕过建议，
未经当前 APK 信任密钥验证或存在文件冲突的管理插件更新会失败，不能用关闭校验解决。
不修改核心上传/更新脚本；此补丁不为核心二进制提供签名证明，核心仍需用户独立校验。
该版本原生初始化会为管理页面流式请求设置 uhttpd `max_requests=50`、
`script_timeout=3600`；这是所选插件的管理界面行为，未额外添加系统性能调整或长期 debug 服务。

## 首次设置与手动核心

以下默认值适用于全新配置；保留旧配置或 U-Boot 的 `owrt_*` 预置可能影响首次登录。
当前旧配置不默认承诺可直接沿用，风险及升级前检查见 [UPGRADE.md](UPGRADE.md)。

1. 经兼容性确认并完成备份后，用有线接入 LAN。默认管理地址为 `192.168.1.1`，
   LuCI 使用 HTTPS（HTTP 重定向，首次为本机生成的证书）。用户名 `root`。
   没有保留/预置凭据时无预设 root 密码，立即在系统 → 管理权设置强密码；
   SSH 登录后也可使用 `passwd`。不提供通用弱密码。
2. LAN 为 `lan1 lan2 lan3` 的 bridge，WAN 为独立 `eth1`。
   上游设备树对应交换机端口 2/1/0 → lan1/lan2/lan3；实际外壳标签由逐口测试确认。
   WAN 默认 DHCP。运营商要求 PPPoE 时，在 WAN 页面填入自己的账号并按运营商要求设置 VLAN。
   基础上网取决于正确的接入配置。
3. 双频无线驱动保留，但 radio 初始关闭。设置所在国家/地区、合规信道、
   独立 SSID 和强密码，选择 WPA2-PSK/SAE 等支持的加密后再启用。
   不预置开放 Wi-Fi 或密码，遵循上游监管域限制；在系统页面设置时区及确认校时。
4. 先确认关闭 OpenClash 时 DNS/DHCP、WAN 和双频 Wi-Fi 正常，再到 OpenClash 的
   核心管理页面选择 **Meta/Mihomo / Linux ARM64（`linux-arm64`）**。
   此设备为 AArch64/Cortex-A53，不选择 ARMv7、MIPS 或 x86。
5. 从可信的 Mihomo 稳定发布来源获取与 ARM64 对应的资产及其发布校验值。
   下载压缩包后先比对 SHA256（`sha256sum 文件名`），用 `gzip -t 文件名.gz` 检查压缩完整性。
   没有可信校验值时不能把“文件可解压”视为来源可信。
   用插件支持的核心上传入口安装；实际可执行文件应为 `/etc/openclash/core/clash_meta`。
   若需手动放置，解压为该路径并设可执行权限，随后执行 `clash_meta -v` 确认版本和架构。
   本任务不下载或执行任何代理核心。
6. 小闪存模式保持关闭。导入你自己的有效配置，先做配置检查，再启用 OpenClash。
   节点/订阅/密钥只保留在本机，不进入仓库或公开构建日志。停用后复测基础 DNS 和联网。
   100M 家庭用途先使用适度规则规模，再根据 CPU/内存、延迟和实际线路情况调整。

## 真机验收

基础系统阶段：确认正常启动和多次正常重启、配置保留、正确 eMMC/overlay 挂载，
逐个 WAN/LAN 测试，2.4/5GHz 的关联/加密/传输，DHCP、DNS、DHCP/PPPoE 上网、校时及 USB。
IPv6 仅在运营商和接入方式实际提供时测试地址、前缀分配及 DNS/访问。
确认 WAN 无管理页面/SSH 暴露、CPU 频率/温度及默认加速状态。

代理阶段：手动安装/校验核心并导入配置后，测试核心/配置重启后保留、OpenClash 启停、
DNS/路由/防火墙、双频与网口联网、IPv4/可用 IPv6、100M 满载下资源/延迟，以及停用后恢复。
观察至少 24～48 小时，记录 OOM、无线重连、异常重启、CPU/内存趋势及错误日志。
没有真机结果不阻止云端构建，但不能承诺绝不掉线、绝不变砖或网络质量。
