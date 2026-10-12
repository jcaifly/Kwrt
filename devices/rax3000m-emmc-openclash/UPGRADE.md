# 升级兼容性、只读采集及待审核备份恢复清单

**当前尚未确认可刷写。** 已知“Kwrt + yuzhuii U-Boot + 卖家调整约 2GB 软件分区”
不能替代具体版本、实际 GPT 和升级路径证据。构建候选固件与确认能刷是不同结论。
本任务不执行备份、恢复、环境变量写入或刷机。

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

## 官方候选的写入路径

以下为固定 OpenWrt v25.12.5 的源码证据；当前已运行系统的行为需另行核对。

| 源码 | 作用及范围 |
| --- | --- |
| `target/linux/mediatek/image/filogic.mk` 的 `Device/cmcc_rax3000m` | 统一 FIT `sysupgrade.itb`，含正式 NAND/eMMC overlay |
| `.../dts/mt7981b-cmcc-rax3000m.dts` | 设备为 `cmcc,rax3000m`，根文件系统为 `/dev/fit0` |
| `.../dts/mt7981b-cmcc-rax3000m-emmc.dtso` | 按名称引用现有 `production` 系统分区和 `factory` 校准分区，不定义/重写 GPT 边界 |
| `.../filogic/base-files/lib/upgrade/platform.sh` | 该 board 使用 `fit_check_image` / `fit_do_upgrade`，eMMC 分支支持配置保存 |
| `package/utils/fitblk/files/fit.sh` | 从当前 DT `chosen/rootdisk` phandle 找到实际块设备，设置 `EMMC_KERN_DEV`；资料不匹配时不能猜分区号 |
| `package/base-files/files/lib/upgrade/emmc.sh` | `emmc_upgrade_fit` 去除 fwtool 尾部信息后，以 dd 更新已识别的系统分区内容 |
| fstools 固定源码 `16718b6e3c0fc7db7be6ae5848db0eae88ac8a8b` 的 `libfstools/fit.c/common.c` | 识别 FIT 根及 `/dev/fitrw`，需要时在该系统分区内初始化可写 ext4/F2FS |

在官方路径下，内核、根 squashfs 及 DT/overlay 同处一个 FIT；升级修改 `EMMC_KERN_DEV`
对应的现有系统分区内容，不向整个 `/dev/mmcblk0` 写 GPT，不更新 BL2、FIP/U-Boot 或 factory。
不保留配置时，会在去除尾部元数据后的镜像末尾之后、系统分区以内写入约 4KiB 的 overlay 初始化标记；
保留配置时，把配置备份写入系统分区内用于下一次启动恢复的区域。
首次启动可能格式化 `/dev/fitrw` 所覆盖的可写区域，**旧 overlay 的应用、配置及存放数据可能被清除**。
这属于系统分区内部文件系统更新，允许范围与 GPT 调整不同；本任务不执行。
可写区域大小和偏移需用实际镜像、目标 GPT 及当前升级脚本核对。

U-Boot 必须支持该 external FIT，正确选择/叠加 `mt7981b-cmcc-rax3000m-emmc` overlay，
并从现有系统分区启动。只会启动传统分开的 kernel/rootfs、不能应用 overlay，
或当前标识为 `cmcc,rax3000m-emmc` 而校验不接受统一 profile 时，不能直接套用候选。
不改扩展名、不伪造 board、不给 `sysupgrade -F` 或忽略兼容版本的建议。
若继续必须改变 GPT、引导或校准数据，停止直接刷写建议并先说明、征求用户决定。
保留已经调整的 2GB 布局仍是本任务边界。

## 当前系统上的预检查

先审查用户反馈的 **当前系统** sysupgrade、validator 和平台脚本，
确认其 `-T`/`--test` 分支确实只校验且在升级前退出，再执行手动测试。
不要仅依据新固件里有该参数推断旧系统支持；二进制验证器来源不明时先补齐源码/版本。

确认后由用户手动把候选复制到 `/tmp`，核对 SHA256SUMS，
再运行当前系统支持的 `sysupgrade -T /tmp/实际文件名-sysupgrade.itb`。
这会产生 `/tmp` 校验临时文件，但不应写系统分区；任何实际兼容错误都必须保留并调查。
没有通过时停止，不使用 `-F`、`--ignore-minor-compat-version`、强装依赖或关闭校验。

SHA256 相同只证明文件一致；`sysupgrade -T` 通过只证明当时脚本的检查通过。
还需交叉验证写入目标、分区容量、U-Boot/overlay 支持和恢复方案，
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
