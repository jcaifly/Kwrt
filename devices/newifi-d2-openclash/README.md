# Newifi D2：OpenClash 管理插件固件（不带内核）

此独立配置只构建 `ramips/mt7621/d-team_newifi-d2`，对应标准 32 MiB SPI NOR 闪存的 D-Team Newifi D2（newifi3）。它不调用原来的公共/MT7621 DIY 脚本，不改动原工作流或其他设备。基础系统使用 OpenWrt 25.12.0，OpenClash 来自 Kwrt 使用的 `kiddin9/op-packages`。

## 来源与配置

所有依赖固定到 [sources.env](sources.env) 中的完整提交，构建记录实际检出的 SHA；Kwrt 自身的版本为触发工作流时的仓库提交。

| 来源 | 固定提交 |
| --- | --- |
| OpenWrt `v25.12.0` | `4da53efc2fe744601e6189492dbd06b8930d72b8` |
| 官方 packages | `506c37591d7cd9b3cfd812e69e708349268f9865` |
| 官方 LuCI | `27a9c0c94264063894d40420956696d19b175744` |
| kiddin9/op-packages | `5ce75c9f2b084c7e3767c630985bb43819f16fbc` |
| OpenClash 包版本 | `0.47.156-8`（APK 为 `0.47.156-r8`） |

仅稀疏检出并导入 `luci-app-openclash`，不导入整个第三方 feed。插件保留原有小闪存模式、手动安装内核、中文页面、规则数据库和管理资源。唯一包补丁是声明 `luci-base/host` 构建依赖，让中文翻译使用的 `po2lmo` 在并行构建前准备好；不改变插件运行代码。

`make defconfig` 后严格检查：只选一个 profile；关闭全设备、全软件包、全 kmod、SDK、ImageBuilder、独立工具链、initramfs 和额外根文件系统格式；保留 MT7603（2.4 GHz）、MT76x2（5 GHz）、WPA、4 个 LAN、1 个 WAN、USB 及设备默认驱动。保留 LuCI 中文界面、DHCP/DNS、PPPoE、IPv6、SSH 和正常路由功能。无线默认沿用官方关闭状态，首次登录后自行设置正确地区、SSID、密码并启用两个射频。

使用官方 firewall4/nftables，预装 `kmod-nft-tproxy`、`kmod-nft-socket`、`kmod-inet-diag`、`kmod-tun`；`dnsmasq-full` 替换 `dnsmasq`/`dnsmasq-dhcpv6`，启用 DHCP、DHCPv6、DNSSEC、nftset。OpenClash 的 Bash、Curl、CA、ip-full、Ruby、ruby-yaml、Unzip 和 LuCI Lua 兼容层一并安装，由配置检查核对依赖闭包及包冲突。不给旧 iptables 防火墙额外混装一套规则。

构建过程中不下载、编译或打包 Mihomo，也不安装其他代理插件或 Docker。默认 `openclash.config.enable=0`，启动项关闭，没有订阅、节点、活动代理配置或首次开机下载脚本。插件在用户主动启用之后的原有更新/缺失内核处理逻辑保持原样。

## 手动触发 GitHub Actions

1. 把本次新增文件提交到你有写权限的**公开** Kwrt fork；工作流文件也需要存在于默认分支，才能在 Actions 中看到手动运行入口。
2. 打开 **Actions → Newifi D2 OpenClash (no core) → Run workflow**，选择包含本次配置的分支并运行。无需配置个人 Token、SSH 密钥、通知服务或作者服务器。
3. 使用普通 `ubuntu-24.04` GitHub 托管 runner；本工作流不使用付费的大型 runner，并对私有仓库跳过构建。没有 push、定时或批量设备触发。
4. 成功后在该运行页面底部下载 `newifi-d2-openclash-firmware-<run_id>` 和 `newifi-d2-openclash-diagnostics-<run_id>`。Artifacts 保留 30 天；不自动创建 Release、不发布到第三方服务器。

CLI 等效命令（`OWNER/REPO` 和 `BRANCH` 替换成你的 fork/分支）：

```sh
gh workflow run newifi-d2-openclash.yml --repo OWNER/REPO --ref BRANCH
gh run list --repo OWNER/REPO --workflow newifi-d2-openclash.yml
gh run download RUN_ID --repo OWNER/REPO
```

`workflow_dispatch` 只有一个固定设备作业。完整编译失败会保留并行日志，再以 `-j1 V=s` 重试并保留详细日志；再次失败仍会失败退出。不会忽略依赖、修改内核 vermagic、强制接受架构或关闭 TLS/源码校验。

固件 Artifact 包含：

- `*d-team_newifi-d2-squashfs-sysupgrade.bin`：唯一设备镜像。
- `SHA256SUMS`：最终 BIN 的 SHA256，可用 `sha256sum -c SHA256SUMS` 检查。
- `final.config`、`diff.config`：最终完整配置和差异配置。
- `packages.manifest`：最终固件包清单，核对 OpenClash 及必要依赖。
- `sources.json`：Kwrt、OpenWrt、各 feed 实际提交、OpenClash 版本及包补丁校验值。
- `profiles.json`、`config-check.json`、`artifact-check.json`：型号、校验、依赖及体积验证证据。
- `README.md`、`VALIDATION.md`：使用说明及此次云端前置检查快照。

诊断 Artifact 保存安装/准备/下载/编译日志、各阶段退出码、最终配置、来源记录、OpenWrt 编译日志归档及磁盘信息。即使上游构建因体积超限只删除镜像而没有非零退出码，产物检查仍会因缺少镜像而失败，不上传固件。

## 闪存和验收界限

上游设备定义的 `IMAGE_SIZE := 32448k`，与 DTS 的固件分区 `0x50000 + 0x1fb0000` 一致：固件允许上限 **33,226,752 字节（31.6875 MiB）**；物理闪存 **33,554,432 字节（32 MiB）**。不扩大分区、不修改引导程序或时钟，不改变上游镜像大小检查。

成功构建时还会独立核对最终 BIN 的大小（含附加元数据）不超过上限，并把实际大小、上限和镜像余量写入 `artifact-check.json`。镜像余量不等于刷机后的可写空间：JFFS2 的擦除块对齐、文件系统元数据及首次启动写入都会影响结果，因此报告不把它当作可靠的剩余可写空间；真机启动后用 `df -h /overlay` 测量。如果插件和必要依赖超过上限，构建必须失败，应先评估体积来源并讨论外置存储/后装插件等方案，不删掉 Wi-Fi、网口或基础联网功能。

云端前置检查状态见 [VALIDATION.md](VALIDATION.md)。配置检查通过、固件编译成功、真机验证是三个不同结论。硬件上的双频 Wi-Fi、所有 WAN/LAN、DHCP、PPPoE/DHCP 上网、DNS、IPv6、防火墙以及日常负载稳定性仍需刷机后测试；本次验收不要求 Mihomo 已安装或代理已运行。

## 刷机前与首次登录

先确认设备确为 Newifi D2、新镜像的型号元数据正确、SHA256 一致。此产物为 **sysupgrade** 镜像，用于兼容的 OpenWrt/Kwrt 升级路径，不能直接把它当作原厂安装或 bootloader 镜像。

在现有系统的 **系统 → 备份/升级** 下载配置备份；另行保存你需要的 OpenClash 配置和其他自定义文件。备份可能包含密码，只保存在你信任的位置。检查当前系统是否涉及旧 swconfig 到 DSA 的迁移，先阅读升级提示；本配置使用官方 DSA 网口定义，建议首次迁移不保留旧网络配置、刷好后手动恢复所需设置。不要使用 `-F` 强制跳过型号或兼容性检查。可在路由器上用 `sysupgrade -T /tmp/固件文件.bin` 做兼容性预检；失败时停止升级并根据提示排查。

本任务不执行刷机，也不连接用户路由器或本地电脑。完成刷机后，通过 LAN 有线连接，访问 **http://192.168.1.1**。新装/不保留旧配置时用户名 **root**，初始未设置密码；首次进入后在 **系统 → 管理权** 设置强密码，也可在路由器 SSH 中执行 `passwd`。WAN 默认 DHCP；如果需要 PPPoE，用户自行填入账号。保留旧配置时管理地址和密码可能延续旧值。

## 之后手动安装 Mihomo

1. 保持 OpenClash 停用。在 **服务 → OpenClash → 插件设置/运行设置** 打开 **小闪存模式** 并保存，确认尚未启动代理。
2. 到版本/内核管理页确认架构为 **`linux-mipsle-softfloat`**（设备包架构 `mipsel_24kc`，MIPS 小端软浮点）；选择适配的 **Meta/Mihomo** 内核。由你主动点击内核安装/更新按钮或上传可信的相应内核，不使用 ARM、MIPS 大端、MIPS64 或硬浮点文件。
3. 手工上传时先解压内核，按插件要求命名 `clash_meta`；小闪存模式使用 **`/tmp/etc/openclash/core/clash_meta`**，文件需要可执行权限。确认内核页识别出版本后，再自行导入配置、检查配置，然后手动启动 OpenClash。固件中没有任何个人订阅或节点。
4. `/tmp` 在 RAM 中，重启会丢失手动安装的内核。重启后先确认内核存在，必要时重新手动安装再启动；本配置没有为此添加下载脚本。

## 云端/本机前置检查（可选）

在已有 OpenWrt 构建依赖的 Linux 环境执行，不需要创建额外 worktree：

```sh
bash scripts/newifi-d2-openclash.sh prepare /tmp/newifi-build /tmp/newifi-artifacts
```

`prepare` 只检出来源、安装选定 feed 包、运行 `defconfig`/`prereq` 和检查，不进行完整固件编译。为保护现有源码，准备阶段遇到已有 source 目录会退出；请使用新的构建目录。完整编译优先交给 Actions。验证脚本也可分别运行：

```sh
python3 scripts/check-newifi-d2.py config /tmp/newifi-build/openwrt /tmp/config-check.json
python3 scripts/check-newifi-d2.py artifact /tmp/newifi-build/openwrt /tmp/artifact-check.json
```
