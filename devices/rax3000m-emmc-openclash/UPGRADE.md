# 升级兼容性、只读采集及待审核备份恢复清单

**当前尚未确认可刷写。** 已知“Kwrt + yuzhuii U-Boot + 卖家调整约 2GB 软件分区”
不能替代具体版本、实际 GPT 和升级路径证据。构建候选固件与确认能刷是不同结论。
本任务不执行备份、恢复、环境变量写入或刷机。

## 重刷入口与已确认的证据

新固件的编译和镜像检查已成功，并与商家参考比较了设备身份、格式、启动参数、
加载地址和两个 payload 的大小，具体见 [FINAL-IMAGE.md](FINAL-IMAGE.md)。
文档中的真机 Wi-Fi/网口/长期观察等待验证项不需要全部在刷机前完成。

在 LuCI 中不保留配置的“重刷”仍使用当前 sysupgrade 后端；
如果使用 U-Boot 恢复页，第一次写入由该 U-Boot 的网页程序完成，
旧系统 sysupgrade/平台脚本/`-T` 及新固件 Linux 容量 guard 均不参与这一次。
本用户选择 yuzhuii U-Boot 恢复页面，暂时无法查看页面：
只需先确认该版本普通固件更新接受 kernel/rootfs TAR `.bin`、沿用现有布局及实际写入对象，
不能仅凭作者名推断。不要把 GPT/引导更新或全盘擦除当作清空配置。
清除旧 overlay/config 的行为也需按该 U-Boot 版本及首次启动逻辑确认。
下面完整只读采集清单供有条件时审计，不要求用户为 U-Boot 路线先执行 Linux `-T`。

## 必需资料及只读采集

先取得：当前完整固件版本/内核、board_name 和 DT compatible、
U-Boot 的具体项目/版本与实际启动配置、完整 GPT 分区名称/起止扇区/容量、
当前启动参数和 rootdisk、当前 sysupgrade/平台/FIT/eMMC 校验及写入脚本。
需要核对 DDR/内存容量和硬件版本；仅凭“算力版”不修改官方共享设备树。

本目录 `collect-device-info.sh` 可由用户在已确认可用的路由器 SSH 中手动运行。
脚本读取已存在的系统/设备树/sysfs 文件，读取少量明确命名的 boot 环境变量，
可用时以 `fdisk -l` 只读显示 GPT；不存在的文件/命令会跳过。
不调用 sysupgrade，不 source/执行升级脚本，不写块设备或 U-Boot，
不读 network/wireless/OpenClash 配置、密码/订阅字段、完整环境变量或原始 factory 内容。
它只把升级脚本打印成文本，脚本里的 dd/格式化命令不会执行。

用户手动把采集脚本放入 `/tmp` 后：

```sh
sh /tmp/collect-device-info.sh > /tmp/rax3000m-readonly.txt
```

这里只将报告写入 RAM 的 `/tmp`，不改持久配置或分区。
**分享前检查报告并遮掉私人启动 URL、Token 或不希望公开的标识；不要发送完整配置/设备备份。**
本次不会自动连接本机/路由器或自动上传报告。
U-Boot 版本若只能从串口日志/恢复页面获知，由用户提供已遮盖私密内容的版本信息，
不据作者名称臆测页面地址、按键时序或恢复协议。

## 本次候选的写入路径

用户上传商家镜像已确认独立 kernel/rootfs eMMC 路径，见
[VENDOR-FIRMWARE.md](VENDOR-FIRMWARE.md)。这是静态文件证据，不能替代实机 GPT。
下面为固定 v25.12.5 加本设备最小补丁的源码逻辑。

| 源码 | 作用及范围 |
| --- | --- |
| `filogic.mk` 的 `Device/cmcc_rax3000m-emmc` | 原生 `sysupgrade-tar` + 元数据，生成 `.bin`；不生成 GPT/引导文件 |
| `mt7981b-cmcc-rax3000m-emmc-kwrt.dts` | 包含完整共用 DTS，真实身份 `cmcc,rax3000m-emmc`；根为 `PARTLABEL=rootfs` |
| 叶 DTS 的 eMMC/factory/wifi 绑定 | 复用官方 eMMC 及本机校准绑定；不定义 GPT 起止或改变现有分区 |
| `filogic/base-files/lib/upgrade/platform.sh` 的该 board 分支 | 原生 TAR 检查、容量检查、`CI_KERNPART=kernel`、`CI_ROOTPART=rootfs`、`emmc_do_upgrade` / 配置保存 |
| `lib/upgrade/rax3000m-emmc.sh` | 只读检查 TAR 成员、实际唯一分区标签、同一 eMMC 及容量；验证和 stage2 写入前再次检查 |
| `package/base-files/files/lib/upgrade/emmc.sh` | 保持上游原生逻辑，分别写入 kernel/rootfs 已有分区 |
| fstools `16718b6e3c0fc7db7be6ae5848db0eae88ac8a8b` 的 `libfstools/rootdisk.c/common.c` | 在 rootfs 分区内、SquashFS bytes_used 的 64 KiB 对齐末尾，建立 loop overlay 并按需初始化 ext4/F2FS |

原官方统一 `cmcc_rax3000m`、共用 DTS 及 NAND/eMMC overlays 保持完整。
它使用 `production` + `/dev/fit0` + external FIT `.itb`，与商家文件的路径不同；
**该统一 `.itb` 验证构建不作为这台设备的升级交付，也不能改名为 `.bin` 来刷。**
本设备补丁仅新增正式 Kwrt 设备路径及对应网口/升级分支，不裁剪共享设备树或伪造标识。

本次 TAR 只有 CONTROL、kernel 和 root。
原生升级先暂时清零 kernel 前 4 KiB，写 root payload 后再写 kernel payload。
不保留配置时，在 root payload 的 64 KiB 对齐末尾清零 4 KiB 作为 overlay 初始化标记；
保留配置时，在该偏移写配置备份，需另计实际备份长度。
首次启动可能格式化 rootfs 分区剩余区域的 loop 文件系统，
**旧 overlay 的配置、应用和存放数据可能被清除**。
这属于现有系统分区内部的文件系统初始化，不改变 GPT 起止、名称和容量。
此 board 分支不写整盘 GPT、BL2、FIP/U-Boot、factory 或 eMMC boot0/boot1。
本任务没有执行这些写入。

容量检查只能确保 payload 及 marker/备份不越界，不能保证剩余空间足够日常运行。
当前旧系统第一次写新镜像仍执行旧升级脚本；新增 guard 不保护那一次旧系统写入。
所以需要先手工核对当前脚本的实际写入对象、两个分区容量、可写空间和恢复入口。
U-Boot 必须能从当前 kernel 分区加载相同结构的 ARM64/LZMA FIT 并使用该 DTB，
实际 DDR、内存及交换机版本也应确认。
目前只知道作者名和卖家描述，不据此猜分区号、恢复 IP 或接受格式。

不改扩展名、不伪造 board，不使用 `sysupgrade -F` 或忽略兼容版本。
如继续必须改变 GPT、引导或校准数据，停止直接刷写建议并先征求用户决定。
保留已经调整的约 2GB 布局仍是本任务边界。

## 当前系统上的预检查

先审查用户反馈的 **当前系统** sysupgrade、validator 和平台脚本，
确认其 `-T`/`--test` 分支确实只校验且在升级前退出，再执行手动测试。
不要仅依据新固件里有该参数推断旧系统支持；二进制验证器来源不明时先补齐源码/版本。

确认后由用户手动把候选复制到 `/tmp`，核对 SHA256SUMS，
再运行当前系统支持的 `sysupgrade -T /tmp/实际文件名-sysupgrade.bin`。
这会产生 `/tmp` 校验临时文件，但不应写系统分区；任何实际兼容错误都必须保留并调查。
没有通过时停止，不使用 `-F`、`--ignore-minor-compat-version`、强装依赖或关闭校验。

SHA256 相同只证明文件一致；`sysupgrade -T` 通过只证明当时脚本的检查通过。
还需交叉验证写入目标、分区容量、U-Boot/内核 FIT 支持和恢复方案，
模拟器启动也不能替代这些实机证据或长期稳定测试。

## 待审核的备份清单（尚未执行）

| 类别 | 内容 | 保存/注意 |
| --- | --- | --- |
| 配置备份 | 当前系统支持的 sysupgrade 配置备份、接入/Wi-Fi 设置、OpenClash 配置/规则/核心版本及包清单 | 私密保存到用户自己的电脑；可能含密码、订阅和 Token，不进 GitHub/公开日志 |
| 分区信息 | GPT 主/备份表、扇区大小、磁盘容量、所有分区起止/名称/UUID、挂载与启动参数 | 先识别已有工具及只读备份方式；确认读回/校验；不“修复”或自动扩容 GPT |
| 本机校准 | **这台机器自己的** factory/EEPROM/MAC 校准区域及校验值 | 按实际 GPT 识别设备/范围；禁止用其他机器的 factory 替代 |
| 本机引导 | 现有 BL2、FIP/U-Boot、环境分区，以及实际使用的 eMMC boot0/boot1（如有） | 按现有 U-Boot 和真实布局确认备份范围；不猜分区序号；私密保存完整性证据 |
| 回退固件 | 已确认适配这个 U-Boot/GPT 的当前可用固件、校验值和对应说明 | 由卖家/当前固件来源取得；候选新固件不能充当已验证回退方案 |

配置备份不含完整 factory、GPT 和引导，不能当作完整恢复方案。
如果当前源码确认支持 `sysupgrade -b`，用户可选择该方式生成配置备份后自行下载；
本任务不执行备份命令。原始分区备份必须先核对名称/边界/工具，不能把 2GB 原始系统备份
直接写进路由器 RAM 导致内存耗尽；应采用适合用户存储介质的手动、只读导出方案。

## 待确认的恢复方案

需要明确：yuzhuii U-Boot 的具体版本、如何进入恢复界面/串口、实际 IP/协议、
它接受的系统镜像格式、写入分区范围，以及当前已知可用固件。
尚缺这些资料，不能宣称一键恢复可用，也不提供猜测的擦除、GPT、BL2/FIP 写入步骤。
正式升级前先由用户确认恢复入口可达，并完成本机备份与可用固件准备。

跨固件版本、设备标识、DSA/无线配置、包管理或 OpenClash 版本变化时，
保留旧配置可能带入错误的接口、DNS/防火墙规则、旧订阅或不兼容服务。
清空重配会丢失 overlay 内配置/应用/数据，必须先备份。
具体采用保留还是清空，应在当前系统和引导兼容性核对后决定，不能预先保证直接沿用。
