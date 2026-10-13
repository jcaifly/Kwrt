# 商家参考固件的静态检查记录

用户更正了参考文件：本记录使用其确认的 7 月 15 日商家固件。
此前上传的 10 月 12 日镜像不再作为这台机器的已知可用参考。
本次从用户提供的公开 GitHub Release 链接下载，校验并只读提取必要资料；
未执行固件程序、首次启动或升级脚本，未连接路由器。

| 项目 | 从正确参考文件得到的结果 |
| --- | --- |
| 文件 | `kwrt-07.15.2026-mediatek-filogic-cmcc_rax3000m-emmc-squashfs-sysupgrade.bin` |
| 大小 | 42,823,953 字节（约 40.84 MiB） |
| SHA256 | `1a6e955f0923489f474fb9a8ecac4cb64527a8c42abf4a47082539f49fd45d43` |
| 真实格式 | 原生 sysupgrade TAR + fwtool 元数据 |
| 成员 | `sysupgrade-cmcc_rax3000m-emmc/{CONTROL,kernel,root}`，没有 GPT/BL2/FIP/factory 镜像成员 |
| 元数据 / DT compatible | `cmcc,rax3000m-emmc`，compat_version 1.0 |
| 系统标记 | Kwrt 25.12-SNAPSHOT，revision 07.15.2026；完整源码提交未由镜像证明 |
| 内核 | Linux 6.12.94；ARM64 FIT、LZMA、嵌入 DTB；两份载荷的 CRC32/SHA1 通过 |
| kernel 成员 | 4,754,820 字节；内核加载和入口均为 `0x48000000` |
| root 成员 | 38,055,936 字节；SquashFS 4/xz，bytes_used 为 38,055,098 |
| 启动参数 | `root=PARTLABEL=rootfs rootwait`，无 bootargs-override/rootdisk |
| 内存 / eMMC 静态声明 | 512 MiB / 8-bit、26 MHz；实际硬件状态待真机测试 |
| factory | 按本机分区名称读取 factory；候选保留官方 eMMC 校准支持 |
| 软件包数据库 | opkg，375 个已登记包；架构为 aarch64_cortex-a53 |
| OpenClash | 软件包数据库中未安装；不据该参考证明 OpenClash 已稳定运行 |
| 额外代理 | 有 luci-app-passwall 和 sing-box；本任务候选不安装这些包 |
| 必要基础包 | dnsmasq-full 2.93-r1、firewall4、MT7915/MT7981 无线及 USB3 |
| 安全升级证据 | kernel 包为 `6.12.94~1-r1`，opkg.conf 未启用 check_signature；不能据此证明远端 ABI 或签名兼容 |

固件结构、fwtool 元数据、FIT 哈希、ARM64 内核标识及 SquashFS 结构检查通过。
只提取升级脚本、发行版、网口设置及软件包元数据，未进行全量用户空间 ELF 审计。
参考镜像的额外软件不会被复制到候选；候选使用固定稳定来源及真实内核 ABI，
不沿用固定 vermagic、忽略依赖或关闭签名的通用绕过设置。

## 升级及启动路径

该文件的 platform.sh 把 `cmcc,rax3000m-emmc` 归入原生 eMMC 分支，设置
`CI_KERNPART=kernel`、`CI_ROOTPART=rootfs`，调用 `emmc_do_upgrade`。
其 emmc.sh 与固定 v25.12.5 的原生文件字节完全一致，SHA256 为
`d4503632578285896b1e9ddaa64d12c163ebcf391cbd5399218d91b6333cd1f6`。
它按已有 GPT 的名称查找分区，不在这个设备分支改写 GPT、BL2/FIP/U-Boot 或 factory。
不保留配置时，会重置 rootfs 内的 overlay；旧配置、应用及相关数据可能丢失。
这些 Linux 脚本不参与用户选定的 U-Boot 网页首次写入。

参考 root 的 64 KiB 对齐末尾为 38,076,416 字节。
Linux 原生初始化标记需至少 38,080,512 字节；保留配置还需计入备份。
所核对公开 Yuzhii U-Boot TAR 代码处理其后 512 KiB，结束位置为 38,600,704 字节。
这些均为相对 rootfs 分区的写入范围，不是本机分区容量或剩余空间测量。
镜像没有 GPT 表，不按整块 eMMC 或“约 2GB”推算空间。

## 与现有候选的对应关系

与此前完整编译通过的候选比较，十项静态字段全部一致：设备兼容标识、
根启动参数、无 bootargs-override/rootdisk、LZMA、加载地址、入口、
内存声明、活动 eMMC 控制器参数和 factory 名称。
候选保持 Kwrt 已有的 `cmcc_rax3000m-emmc` 和 kernel/rootfs TAR 路径，
保留官方共享 DTS、统一 profile 和 NAND/eMMC overlays。
更正参考后无需改变分区或引导，也没有依据将官方统一 .itb 改名交付。
新版 USB 与 APK 签名改进不会改变这个镜像封装和分区选择。

卖家确认机器运行 Kwrt，分区已经做好。参考及公开写入代码提供了具体兼容基础。
普通重刷不要求先取得 U-Boot 的完整源码提交与编译配置；
使用卖家的普通固件更新入口，保留正确商家固件作为回退候选，页面报错时停止处理。
本机当前恢复页面和实际 GPT 仍未读取，状态为候选固件、尚未确认可刷写。
Wi-Fi、网口、重启、基础联网及手动安装核心后的代理仍待真机验证。

[正确参考文件下载](https://github.com/jcaifly/Kwrt/releases/download/%E5%90%88%E6%A0%BC%E7%9A%84%E5%8C%85/kwrt-07.15.2026-mediatek-filogic-cmcc_rax3000m-emmc-squashfs-sysupgrade.bin)
