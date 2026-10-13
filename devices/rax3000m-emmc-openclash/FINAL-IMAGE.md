# 本次固件交付与商家参考对照

**完整编译、自动镜像验收和上传文件的独立检查通过；真机未测试。**
用户计划通过 yuzhuii U-Boot 恢复页面重刷，暂时无法查看页面。
两份镜像的升级格式及启动参数一致；实际 U-Boot 版本、网页支持格式与写入范围
尚未确认，不能据此宣称已确认可从该恢复页刷写。无需因约 2GB 分区而重新分区。

## 成功构建与下载

- 运行：[38336069750](https://github.com/jcaifly/Kwrt/actions/runs/38336069750)，
  北京时间 2026-10-13 12:49 完成，编译、镜像检查、固件和诊断上传均成功。
- 实际构建入口提交：`69a0deb88550dff98882d493343243959ae73920`。
- 镜像：`kwrt-25.12.5-mediatek-filogic-cmcc_rax3000m-emmc-squashfs-sysupgrade.bin`。
- 大小：**21,432,593 字节，约 20.44 MiB**。
- 镜像 SHA256：
  `9cda5d704a8129a9e45b0883e6f612a3caffccabdc65e4cea6f0b6e81f5beb2b`。
- 该运行的 `rax3000m-emmc-openclash-candidate-38336069750` 附件含镜像、
  SHA256SUMS、final.config、kernel.config、diff.config、packages.manifest、
  profiles.json、sources.json、检查结果及使用/备份说明。
- `rax3000m-emmc-openclash-diagnostics-38336069750` 附件含构建日志及诊断，
  附件保存 30 天。登录仓库账号后从该运行的 Artifacts 下载。
  固件附件的 ZIP digest 与上述镜像 SHA256 是不同对象的校验值。

## 已验证的实际镜像

| 项目 | 证据 / 结果 |
| --- | --- |
| 上传文件与 Actions 一致性 | 整个 BIN 的 SHA256 和大小均与公开成功记录完全一致 |
| 格式 | 原生 sysupgrade TAR + fwtool 元数据；只有 CONTROL、kernel、root，无 GPT/引导/factory 镜像 |
| 型号 / 兼容版本 | cmcc,rax3000m-emmc / compat_version 1.0 |
| 内核 FIT | ARM64、LZMA、内核和 DTB 的 CRC32/SHA1 均匹配 |
| 根文件系统 | SquashFS 4，解包和普通文件读取通过 |
| 包清单 | 实际 APK 数据库 226 包；CI 另核对最终 manifest 与数据库完全相同 |
| OpenClash | 0.48.002-r9，管理插件和必要依赖完整；默认停用，小闪存模式关闭 |
| Mihomo / 私人代理配置 | 未预装核心，无个人订阅或代理配置 |
| 内核包及 ABI | 6.12.94~9127b7d13b17ee62d508f2f4aaa555f4-r1；69 条内核 ABI 依赖一致 |
| 用户空间架构 | 240 个 ELF 核对为 AArch64；硬件内部固件另行保留 |
| 软件源 | 25.12.5 官方 mediatek/filogic 及 aarch64_cortex-a53 base/packages/luci；无虚构 OpenClash APK 源 |
| 安全默认值 | 与审核脚本完全一致；无核心自动下载、无新增分区/引导操作；两种 flow offloading 关闭 |

独立解包只因云端无权创建 `/dev/console` 字符设备而返回 2，普通文件全部解出。
不执行任何目标架构程序或固件内脚本，镜像未修改。
远端官方 kmod ABI 仍不能仅凭发行版号判定一致，新增模块应使用同一实际内核 ABI。

## 参考固件已实际用于适配

| 项目 | 商家固件 | 本次固件 |
| --- | --- | --- |
| 设备身份 | cmcc,rax3000m-emmc | 相同 |
| 升级成员 | kernel + root 的 TAR | 相同 |
| 根启动参数 | root=PARTLABEL=rootfs rootwait | 相同 |
| 内核压缩 / 加载及入口 | LZMA / 0x48000000 | 相同 |
| 内存声明 / eMMC 控制器参数 / factory 名称 | 512 MiB / 8-bit、26MHz / factory | 相同，实际硬件状态仍待验证 |
| kernel 长度 | 4,772,360 字节 | 4,498,488 字节 |
| root payload 长度 | 24,103,936 字节 | 16,920,576 字节 |
| Linux 原生 emmc.sh | 商家文件内脚本 | 字节完全相同；U-Boot 首次刷写不会执行此脚本 |

如果这台机器确实运行该商家镜像，且 GPT 没有再次改变，新镜像两个 payload
分别小于已有 payload，支持“无需因镜像体积改变布局”的判断。
独立 eMMC profile 没有固定 IMAGE_SIZE，实际允许上限应分别取现有 kernel/rootfs 分区。
本次 root payload 的 64 KiB 对齐末尾为 16,973,824 字节；
原生 Linux 升级需至少 16,977,920 字节容纳初始化标记，保留配置时还要计入备份。
这不是实机分区测量，也不代表足够可写空间；没有实际 GPT，不能可靠估算剩余空间。

## “未采集”哪些会影响重刷

Wi-Fi、网口、联网、24～48 小时运行和手动安装核心后的代理测试属于真机验收，
不能在刷机前完成，不代表固件编译或制作不完整。
重刷入口决定刷机前需要的检查：

- **当前系统 LuCI / SSH：**清空配置的重刷仍由当前 sysupgrade 后端处理，
  应核对当前脚本、设备身份和分区；清空配置不等于改 GPT 或重装 U-Boot。
- **本用户选择的 U-Boot 恢复页：**旧系统 sysupgrade / `-T` 不参与第一次写入，
  新固件内的 Linux 容量 guard 同样不保护这一次。
  需确认该页面的普通固件更新能解析这种 TAR `.bin`，使用当前 kernel/rootfs 布局，
  不执行 GPT/引导/factory 更新。仅作者名称或 `.bin` 后缀不能证明这些行为。

暂时无法查看页面时，只标记这项兼容性待确认，不要求用户重复大份系统采集。
不能给出直接点击确认刷写的结论，也不能推断 U-Boot 更新一定清除旧配置：
overlay 初始化及清除行为应以该版本的写入逻辑、页面选项和首次启动逻辑为依据。
Linux 原生不保留配置路径会重置并初始化 rootfs 分区内的 overlay，旧数据可能丢失；
本任务不执行。不要把全盘擦除或 GPT 更新当成“清空配置”。

此前商家固件应私密保存为回退候选，结合同一 U-Boot 确认恢复入口和接受格式。
配置备份与本机 factory/引导/GPT 备份是不同内容，清单见 UPGRADE.md。
不以另一台机器的 factory 替代本机校准数据，不虚构一键恢复。

## 实际来源

| 组件 | 提交 |
| --- | --- |
| Kwrt 构建入口 | 69a0deb88550dff98882d493343243959ae73920 |
| OpenWrt v25.12.5 | f0a60eee2fe051741c643ea6118718aae1ef17fb |
| packages | 5caa62e0bc9f7fb9b0c12a23267bceb7724214dd |
| LuCI | 128a7812f4be233c5dd7f7466f534fd888785caf |
| OpenClash 0.48.002-r9 | 426eda7eae561e63b6dc78f4c6bcaa4105ca4b16 |

运行的 sources.json 另含必要设备和插件补丁 SHA256。
镜像原生 DISTRIB_REVISION / fwtool revision 为 `r33051-f5dae5ece4`，
来自固定 OpenWrt 源码的发行版 version 文件；DISTRIB_DESCRIPTION 含实际源码前缀
`f0a60eee2fe0`。完整提交以 sources.json / 上表为准，不通过伪造 revision 或 ABI 解决问题。
使用及默认管理地址、WAN/Wi-Fi、ARM64 核心手动安装和两阶段真机清单见 README.md。
