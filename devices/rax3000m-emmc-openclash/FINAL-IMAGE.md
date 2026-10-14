# 新版候选固件交付记录

**运行 38419054903 完整编译、自动镜像检查及同次签名包仓库验证通过；真机未测试。**
这是补齐 USB 存储及签名软件包的新版。下文历史中的旧大小、旧 ABI 和旧 SHA256
不适用于这次新版；两次运行的 BIN 文件名相同，下载时按运行号和哈希区分。

## 本次实际结果

- 运行：[38419054903](https://github.com/jcaifly/Kwrt/actions/runs/38419054903)，
  北京时间 **2026-10-14 02:28** 完成，耗时约 3 小时 23 分钟。
- 实际构建入口：`3df480802ab87cf999c6508d8f462b10c3cbe146`，
  审核分支 `codex/rax3000m-emmc-openclash`；未合入或推送默认分支。
- 镜像：`kwrt-25.12.5-mediatek-filogic-cmcc_rax3000m-emmc-squashfs-sysupgrade.bin`。
- 大小：**21,514,513 字节，约 20.52 MiB**；比上一版增加 81,920 字节（80 KiB）。
- 整个 BIN 的 SHA256：
  `b7dcad99e9481b42477adc3e4eabf2e748f8687c24cfd95bd287eb9fc087bb8b`。
- 实际安装 **233 包**，OpenClash **0.48.002-r9**；配套仓库为 **233 个签名 APK**。
- 实际 Linux 内核包及 ABI：
  `6.12.94~be9e1284de3f4381ab48ad821ca31119-r1`。
- Mihomo 未下载、编译或预装；OpenClash 默认停用，小闪存模式关闭。

## 下载及检查记录

登录 GitHub 后打开同次运行的 Artifacts；附件保留 30 天，建议同时保存三份：

| 附件 | 内容 |
| --- | --- |
| [rax3000m-emmc-openclash-candidate-38419054903](https://github.com/jcaifly/Kwrt/actions/runs/38419054903/artifacts/11839460358) | 本次 BIN、SHA256SUMS、final.config、kernel.config、diff.config、packages.manifest、profiles.json、sources.json、检查 JSON 和使用/备份说明 |
| [rax3000m-emmc-matching-packages-38419054903](https://github.com/jcaifly/Kwrt/actions/runs/38419054903/artifacts/11839425371) | 与该镜像匹配的 233 个签名 APK、签名索引、公开密钥、SHA256SUMS 和仓库验收记录 |
| [rax3000m-emmc-openclash-diagnostics-38419054903](https://github.com/jcaifly/Kwrt/actions/runs/38419054903/artifacts/11838576557) | 编译及前置检查日志、原生仓库测试日志、来源/配置/镜像/仓库报告及阶段诊断 |

公开页面显示的 ZIP digest 为：

- candidate：`7b8d296b2ebcb7fee10e019dd04fe860c4369593e883dd06dd818e7fb48e8e22`
- matching-packages：`bbfdba276a0dc93d6ffe87092706acfbf7dd029851d2a92733340e207bcc73fd`
- diagnostics：`d092ce6e288cb0ae9d793032117e3334f55c9952621d6bcded0b219ad2bd46fb`

ZIP digest 与 BIN 的 SHA256 对应不同文件。解压后用 SHA256SUMS 核对 BIN；
Windows 可用 `Get-FileHash -Algorithm SHA256`，Linux 可用 `sha256sum`，
macOS 可用 `shasum -a 256`。
软件包仓库只与本次镜像及其原生信任密钥配套，不能因为发行版标签相同而混用其他运行。
不把全量 `apk upgrade` 当作系统升级，不强装不同内核 ABI 的模块；使用方式见 PACKAGES.md。

## 已检查与待验证

证据为公开运行、[job 步骤](https://github.com/jcaifly/Kwrt/actions/runs/38419054903/job/115371186559)
及 `Verified candidate record` 注释，已核对它们指向上面的实际入口提交。
编译、最终设备配置/来源、自动镜像验收、原生包仓库检查、三份上传和汇总均为 success。

| 项目 | 本次证据与状态 |
| --- | --- |
| 最终配置及依赖 | 本地真实 defconfig/prereq 通过；CI 在编译前后再次核对单设备、驱动、依赖及冲突 |
| 完整编译 | GitHub Actions 成功，实际镜像大小与哈希来自该次检查结果 |
| 自动镜像检查 | TAR/FIT/型号元数据、SquashFS 信息、manifest 与最终 APK 数据库、用户空间架构、真实 ABI、中文及安全默认值通过 |
| 同次软件包仓库 | 233 包；原生工具核对单包及索引签名、安装内容身份、架构、ABI、离线依赖闭包通过；不导出私钥 |
| 回归检查 | 本地 39 项通过；CI 回归步骤通过，并在构建后使用当次 host 工具完成 10 项仓库测试 |
| 新 BIN 的独立云端解包 | 用户上传本次 ZIP 后完成；唯一 BIN、ZIP/BIN 哈希、TAR/FIT/型号元数据、实际文件系统及 233 包均相符；248 个 AArch64 ELF、75 条内核 ABI 依赖通过 |
| 当前系统预检查 | 未执行；用户选择 U-Boot 首次重刷，旧系统 sysupgrade 不参与该次写入 |
| 实际 GPT、U-Boot 恢复页及写入逻辑 | 尚未核对本机页面；已有正确商家镜像和源码的静态适配依据 |
| 双频 Wi-Fi、WAN/LAN、USB、重启、配置保留、联网及 24～48 小时观察 | 待真机验证 |
| 手动安装 ARM64 核心、导入配置后的 OpenClash 和停用恢复 | 待真机验证，本次未安装核心 |

本独立 eMMC profile **无固定 IMAGE_SIZE**。允许上限取自实际 kernel/rootfs 分区，
不按“2GB 软件分区”或整个 eMMC 总容量估算。独立解析本次 BIN 得到：
kernel 为 **4,501,716 字节**，root payload 为 **17,001,472 字节**，
SquashFS 实际使用 17,001,392 字节，64 KiB 对齐后的 overlay 偏移为 17,039,360 字节。
Linux 原生升级加上 4 KiB 初始化标记最低需 17,043,456 字节；
这些与本次 artifact-check.json 完全一致，不代表足够可写空间或 U-Boot 写入边界。
缺少本机 GPT，无法可靠估算剩余可写空间。

本次 ZIP 的 CRC 及整包 SHA256、唯一 BIN 的大小及 SHA256 与 Actions 完全一致。
原生 fwtool 从实际 BIN 读取的元数据与报告相符；静态解析 TAR/FIT、核对内核/DTB 哈希，
并实际解包 SquashFS 核对数据库、manifest、中文、模块、软件源、安全默认值和无核心。
不执行任何固件程序或附件内脚本。非 root 解包仅因无法创建 `/dev/console` 字符设备
返回 2，普通文件已解出并检查通过；这不是启动或真机测试。

## 使用与兼容性边界

普通系统刷写对象仅为上述 `.bin`，不刷 GPT、BL2、FIP/U-Boot 或 factory，
不修改现有布局，也没有自动扩容脚本。正确 7 月 15 日商家参考已实际下载核对；
使用相同 eMMC 身份、kernel/rootfs TAR 和 rootfs 启动路径的设备补丁未在此次重制中改变。
这些是具体适配依据，不因没有真机而把已完成构建判为失败，也不把约 2GB 容量当作重分区理由。

用户选择 yuzhuii U-Boot 普通固件恢复入口。首次写入使用该 U-Boot 的逻辑，
不会执行新系统中的 Linux 容量 guard。使用与商家镜像相同的普通固件更新栏目，
如页面提示格式、型号或容量不符，应停止，不改后缀、不绕过检查，也不切换 GPT/引导更新栏目。
当前页面及本机实际布局未核对，交付标为 **候选固件，尚未确认可刷写**。
旧配置和 overlay 数据是否保留取决于实际写入/初始化过程，不默认承诺可直接沿用；
从商家多应用/opkg 系统转到本 APK 系统，建议备份后重新配置，勿直接恢复整套旧系统文件。

默认管理地址 `192.168.1.1`、用户名 `root`；全新配置无预设密码，首次登录立即设置。
WAN 默认 DHCP，PPPoE/VLAN 按运营商要求设置；双频无线初始关闭，设置合规地区、SSID、
加密及强密码后开启。先检查 OpenClash 停用时的基础联网，再手动校验并安装
Mihomo `linux-arm64`，导入自己的配置后启用，小闪存模式保持关闭。
备份与恢复清单、U-Boot 写入边界见 UPGRADE.md；首次设置与两阶段真机检查见 README.md。

## 实际源码

| 组件 | 本次提交 |
| --- | --- |
| Kwrt 构建入口 | 3df480802ab87cf999c6508d8f462b10c3cbe146 |
| OpenWrt v25.12.5 | f0a60eee2fe051741c643ea6118718aae1ef17fb |
| packages | 5caa62e0bc9f7fb9b0c12a23267bceb7724214dd |
| LuCI | 128a7812f4be233c5dd7f7466f534fd888785caf |
| OpenClash 0.48.002-r9 | 426eda7eae561e63b6dc78f4c6bcaa4105ca4b16（kiddin9/op-packages 的插件目录） |

实际补丁 SHA256、配置和完整软件包清单随本次附件交付。以下历史是上一版证据，
不作为新版 BIN 已独立下载解包或真机验证的结论。

---

## 历史：上一版已验证镜像与正确商家参考对照

本记录对应运行 38336069750 已编译的镜像。USB 存储及同次签名 APK 仓库的重制版
使用新的运行记录和实际 SHA256；不能把下列上一版大小、包数或哈希当成新版结果。
用户已更正参考：实际商家固件为 7 月 15 日文件，云端已重新下载检查；
此前 10 月 12 日文件不再用于本机适配判断，正确静态记录见 VENDOR-FIRMWARE.md。

**完整编译、自动镜像验收和上传文件的独立检查通过；真机未测试。**
用户计划通过 yuzhuii U-Boot 恢复页面重刷，暂时无法查看页面。
两份镜像的升级格式及启动参数一致；实际 U-Boot 版本、网页支持格式与写入范围
尚未确认，不能据此宣称已确认可从该恢复页刷写。无需因约 2GB 分区而重新分区。

### 成功构建与下载

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

### 已验证的实际镜像

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

### 参考固件已实际用于适配

| 项目 | 商家固件 | 本次固件 |
| --- | --- | --- |
| 设备身份 | cmcc,rax3000m-emmc | 相同 |
| 升级成员 | kernel + root 的 TAR | 相同 |
| 根启动参数 | root=PARTLABEL=rootfs rootwait | 相同 |
| 内核压缩 / 加载及入口 | LZMA / 0x48000000 | 相同 |
| 内存声明 / eMMC 控制器参数 / factory 名称 | 512 MiB / 8-bit、26MHz / factory | 相同，实际硬件状态仍待验证 |
| kernel 长度 | 4,754,820 字节 | 4,498,488 字节 |
| root payload 长度 | 38,055,936 字节 | 16,920,576 字节 |
| Linux 原生 emmc.sh | 商家文件内脚本 | 字节完全相同；U-Boot 首次刷写不会执行此脚本 |

如果这台机器确实运行该商家镜像，且 GPT 没有再次改变，新镜像两个 payload
分别小于已有 payload，支持“无需因镜像体积改变布局”的判断。
独立 eMMC profile 没有固定 IMAGE_SIZE，实际允许上限应分别取现有 kernel/rootfs 分区。
本次 root payload 的 64 KiB 对齐末尾为 16,973,824 字节；
原生 Linux 升级需至少 16,977,920 字节容纳初始化标记，保留配置时还要计入备份。
这不是实机分区测量，也不代表足够可写空间；没有实际 GPT，不能可靠估算剩余空间。

### “未采集”哪些会影响重刷

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

### 实际来源

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
