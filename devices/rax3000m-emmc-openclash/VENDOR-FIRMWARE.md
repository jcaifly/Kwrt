# 商家固件的静态检查记录

证据为用户上传的镜像文件，不是实机读取结果。本任务未执行其中的程序、
首次启动脚本或升级脚本，也未连接路由器。

| 项目 | 从文件得到的结果 |
| --- | --- |
| 文件 | `kwrt-10.12.2026-mediatek-filogic-cmcc_rax3000m-emmc-squashfs-sysupgrade.bin` |
| 大小 | 28,887,313 字节（约 27.55 MiB） |
| SHA256 | `e2ef62e711033ca20dab31c5b058f2ae3aaa94f33e77f7531b6ff1d9051ebfcf` |
| 真实格式 | 原生 sysupgrade TAR + fwtool 元数据；不是改名的 FIT `.itb` |
| 成员 | `sysupgrade-cmcc_rax3000m-emmc/{CONTROL,kernel,root}`，无 GPT/BL2/FIP/factory 镜像 |
| 元数据及 DT compatible | `cmcc,rax3000m-emmc`，compat_version 1.0 |
| 系统标记 | Kwrt 25.12-SNAPSHOT，revision 10.11.2026；不能凭文件名日期替代版本证据 |
| 内核 | Linux 6.12.112；ARM64 FIT，LZMA 内核和独立 DTB |
| 包架构 | aarch64_cortex-a53；379 个用户空间 ELF 检查为 AArch64 |
| 根文件系统 | SquashFS 4，xz；payload 24,103,936 字节，bytes_used 24,103,072 |
| 内核成员 | 4,772,360 字节，FIT 内核及 DTB 的 CRC32/SHA1 均匹配 |
| 启动参数 | `root=PARTLABEL=rootfs rootwait`，无官方 `/dev/fit0` rootdisk 路径 |
| 设备树内存声明 | 512 MiB；这不是实机内存测量，也不据“算力版”调整 |
| eMMC 校准 | 按名称读取本机 `factory`；EEPROM 0x0，MAC 0x24/0x2a |
| 软件包数据库 | opkg，334 个已登记包；包清单不能证明其远端源兼容性 |
| OpenClash | 0.47.156-r8，默认停用，小闪存模式关闭 |
| Mihomo | 未发现核心文件/核心包或用户空间 ELF 中的 Mihomo 标记 |
| 基础组件 | dnsmasq-full、firewall4/nftables、Ruby/YAML、TUN、MT7915/MT7981 无线及 USB3 |
| 软件源 | `https://dl.openwrt.ai/releases/25.12/...`，内核源路径为 6.12.112 |
| 软件包签名 | 镜像的 opkg.conf 未启用 `check_signature` |
| 流量卸载 | 镜像防火墙配置的软件/硬件 flow offloading 都为 1；实机状态仍待读取 |
| 额外应用 | 包含 partexp、diskman、advancedplus、upnp、fan、syscontrol 等 LuCI 应用 |

TAR、fwtool 元数据、内核 FIT 哈希、ARM64 标识和 SquashFS 结构检查通过。
云端只读解包无法创建 `/dev/console` 字符设备，解包返回 2；普通文件已解出，
日志只有这一项权限限制，不将其误报为镜像损坏。没有执行目标架构程序。
这些静态检查不证明来源经过可信签名，也不证明长期稳定、网络质量或适合当前机器刷写。
镜像中未提供足以固定完整 Kwrt/OpenWrt/feeds 来源的提交记录。
其 kernel 包版本使用 `6.12.112~1-r1`；版本相同不能证明远端 kmod ABI 相同，
尤其原仓库存在固定 vermagic 的通用补丁。本构建不沿用该绕过。

## 文件内的升级写入路径

`lib/upgrade/platform.sh` 对 `cmcc,rax3000m-emmc` 设置
`CI_KERNPART=kernel`、`CI_ROOTPART=rootfs`，调用 `emmc_do_upgrade`。
`find_mmc_part` 按现有 GPT 的 PARTNAME 查找分区，不在这个 board 分支改 GPT。
`emmc_upgrade_tar` 先暂时清零 kernel 分区前 4 KiB，写 root payload，
再写 kernel payload。未保留配置时，在 root payload 的 64 KiB 对齐末尾处
清零 4 KiB 作为 overlay 初始化标记；保留配置时，配置备份写到该对齐偏移。
此 board 分支未写 BL2、FIP/U-Boot 或 factory。
不能把脚本中其他设备分支的引导写入误认为这台设备的行为。

只依据此文件，kernel 分区至少需要 4,772,360 字节；rootfs 分区至少需要
24,121,344 字节才能容纳 payload 和初始化标记。这是最低写入范围，
不是实际分区容量，也不代表剩余可写空间足够，保留配置还要计入备份长度。
文件内没有 GPT 表，无法确认卖家说的“2GB”对应哪个分区、起止扇区或可写空间。
首次启动的 overlay 格式化仍可能清除旧配置、应用及系统分区内数据。

文件中的 sysupgrade 有 `-T/--test` 分支，并在实际升级前退出；
这只能证明上传文件中的脚本文本。实机已安装脚本及二进制 validator
的实际版本/来源仍待核对，不现在宣称预检查已经通过。
分区扩容工具的存在不证明其已执行或首次启动自动扩容，不能据此推断 GPT。

## 对本次候选构建的影响

使用 Kwrt 已有的 `cmcc_rax3000m-emmc` 设备身份及独立 kernel/rootfs TAR 路径。
`kwrt-emmc-layout.patch` 在固定稳定版源码中增加对应 profile 和薄 eMMC DTS，
复用官方共用 DTS、eMMC/factory 校准绑定，保留原统一 profile 及 NAND/eMMC overlays。
不会将 `.itb` 改名或伪造支持列表来通过旧系统检查。
增加的容量检查只读取实际分区信息，并在验证及 stage2 写入前拒绝越界或含糊的分区标签。
仍使用原生 sysupgrade 校验、eMMC 更新及 fstools rootdisk/overlay 逻辑。

此前统一 `cmcc_rax3000m` 的 `.itb` 验证构建不作为这台卖家改版设备的升级交付。
本次最终候选应为 `*cmcc_rax3000m-emmc-squashfs-sysupgrade.bin`。
**路由器尚未到手，实际 GPT、U-Boot、当前系统预检查、硬件和代理测试仍待验证；尚未确认可刷写。**
这个商家镜像可先私密保存为回退候选，但恢复入口、接受格式、写入范围和实际可回退性
必须结合现有 U-Boot 确认，不能据文件检查宣称恢复已验证。
