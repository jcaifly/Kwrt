# RAX3000M eMMC：商家软件组合 + OpenClash + Mihomo

用户要求根据已核对的 7 月 15 日商家固件重新构建全部软件组合，并新增 OpenClash 和
Mihomo。本目录独立于原来的精简版，旧配置和工作流不改动。
只构建 mediatek/filogic 的 `cmcc_rax3000m-emmc`，沿用已实际刷入成功的
kernel/rootfs TAR 路径，不生成或刷写 GPT、BL2、FIP、U-Boot、factory，也不自动扩容。

## 完整清单及对应关系

- [vendor-packages.manifest](vendor-packages.manifest)：商家实际已安装的 **375 包及版本**。
- [PACKAGE-MAP.md](PACKAGE-MAP.md)：375 项完整对应表；机器可读数据见 package-map.json。
- config：本次实际 `make defconfig` 生成的配置审阅快照。
  工作流以完整 vendor inventory、固定源码元数据及脚本明确的安全/依赖设置生成配置，
  再检查所有对应项，不通过删包或忽略依赖来接受缺失项。

保留商家 17 个 LuCI 应用：advancedplus、diskman、fan、filemanager、firewall、
gpsysupgrade、istorex、package-manager、partexp、passwall、quickstart、store、
syscontrol、ttyd、upnp、wifihistory、wizard，以及它们对应的客户端、库及内核模块。
额外加入 OpenClash 0.48.002-r9 和官方 Mihomo v1.19.32 ARM64。
原来排除额外应用和核心的限制按本次明确要求更新，基础网络功能和分区边界不变。

## 明确差异

这份构建复刻软件组合，不宣称所有旧版本或行为原样一致：

- **opkg → APK**：采用 25.12 原生包格式，保留包管理功能。iStore 选择上游 APK 后端。
  不使用商家的假内核 ABI `~1`，也不强装旧 IPK。
- **my-default-settings**：用同名、本设备的安全默认设置包替代。
  原上游脚本设置 root/root、关闭 HTTPS/DNS 重绑定保护并开启加速/性能参数，
  不符合本任务保留的安全边界。本构建不预设密码、不关闭这些保护、不自动跑 benchmark。
- **luci-lib-fs**：使用从校验过的商家镜像只读提取的 Apache-2.0 纯文本 Lua 源码，
  作者、许可证和源码 SHA256 记录于 packages/luci-lib-fs/SOURCE.md；
  其依赖的 nixio 由新源码构建。没有复用商家 ELF、内核模块或任何配置、校准数据。
- **版本更新/对应**：库的 ABI 后缀映射到源码符号；普通包采用固定 25.12 feeds 的版本，
  vendor 特有应用采用固定 kiddin9/op-packages 提交。原/新版本完整列于对应表。
  原生 full sing-box 为 1.12.17，商家为 1.13.14；本构建不把两个版本写成相同。
- **Kconfig 兼容**：固定 Passwall 的实际客户端集合并直接声明全部依赖，
  去掉它自依赖的编译选项菜单；仅去掉未使用 sing-box-tiny 的构建入口，保留 full 版。
  这修复 25.12 递归依赖，不关闭 `RECURSIVE_DEP_IS_ERROR` 或任何依赖/架构/ABI 检查。
- **FullCone**：商家有 kmod-nft-fullcone。新构建重编译同一模块源码，
  加入固定 ImmortalWrt 25.12 来源的 conntrack 多监听者及 nftables/libnftnl/firewall4
  支持补丁，使模块及配置路径配套。FullCone 和软件/硬件 flow offloading **均默认关闭**；
  不把这些功能的存在当成游戏延迟修复证明，不增加发射功率、超频或其他加速补丁。
  libnftnl 同时应用该固定上游的 `PKG_FIXUP:=autoreconf` 配套设置，在 configure 前
  使用 OpenWrt 构建工具重生成修改过的 Makefile；原始失败及局部验证见 [BUILD-FAILURES.md](BUILD-FAILURES.md)。
- **源码校验**：vendor 配方存在 `PKG_HASH:=skip` / `PKG_MIRROR_HASH:=skip`。
  本设备构建固定下载 SHA256；Git 源码按固定提交归档并验证，记录于 source-hashes.json。
  simple-obfs 的 libcork 子模块按父项目 Git 树的确切提交单独下载、校验并还原；
  三个经过 Git→归档替换的源码及其递归子模块在完整编译前检查，缺少或未固定的子模块会立即失败。
  子模块来源、提交和 SHA256 同时写入 sources.json；原有九个顶级下载的 SHA256 保留。
- **APK 版本格式**：Git 快照日期按 OpenWrt 的 `include/download.mk` 使用点分日期，
  FullCone 为 `2023.05.17~07d93b62`；风扇控制配方的重复修订号 `1.0.0-r3-r1`
  整理为 `PKG_VERSION=1.0.0`、`PKG_RELEASE=3`，生成 `1.0.0-r3`，其程序源码保留。
  工作流先构建本次所需的原生 host 工具和 APK，用真实 APK 校验全部选中包的版本元数据，
  再进行完整交叉编译。已知内核/库占位符仅做后缀语法探测，LuCI 的 `x` 动态版本单独列为待生成；
  探测值不会写回任何配方、包或 ABI。真实版本及内核 ABI 仍以最终包和镜像验收为准。
- **预构建程序**：Mihomo 使用官方、校验过的 ARM64 发布文件；quickstart 和 chinadns-ng
  的上游配方同样使用发布者 ARM64 文件，已固定 SHA256，不能称为本次重新编译其源码。
  不执行这些目标程序来伪造运行验证。
- **旧安装绕过**：去除 gpsysupgrade 的自动 IPK 恢复和强制依赖/校验 profile，
  iStore APK 安装不使用 allow-untrusted/强制覆盖。OpenClash 的原 APK 更新校验补丁保留。

## 默认运行和首次设置

管理页面改为商家软件组合的 nginx + uWSGI + LuCI；使用原生 nginx HTTPS 自签名配置，
HTTP 跳转 HTTPS。地址仍为 `https://192.168.1.1`，用户名 root；全新配置没有预设密码，
首次登录立即设置强密码。浏览器首次自签名提示是证书信任问题，不能当作公网身份验证通过。
默认 WAN 为 DHCP，PPPoE/VLAN 依运营商要求设置；LAN 为 lan1/lan2/lan3，WAN 为 eth1。
双频无线驱动保留，首次设置合规地区、信道、加密和密码后启用，不预置开放 Wi-Fi。

Mihomo 已装在 `/etc/openclash/core/clash_meta`，不启用小闪存模式。
OpenClash、Passwall、独立 sing-box 默认停用；不预置订阅、节点或代理 YAML。
导入自己的有效配置并检查后再启动 OpenClash，勿同时启用两套代理接管 DNS/路由。
不启动 autocore/coremark 的性能修改或跑分、ttyd 终端、UPnP 自动映射或 smartd；
软件和内核模块仍保留，用户按用途手动管理。Quickstart 属于本次选择的仪表盘服务；
不启动它额外的 startdhns 网络服务，不添加无关定时任务、重启或测速脚本。
磁盘/分区管理应用可做手动操作，不代表获得改动现有 GPT/引导/factory 的建议；不要用其扩容按钮改变布局。

保留官方 HTTPS 25.12.5 mediatek/filogic 和 aarch64_cortex-a53 的 APK 源。
iStore 另提供明确的 HTTPS 公共 `all/compat` 仓库及其验证公钥；
未证明其所有包或远端官方 kmod 与此内核 ABI 兼容，原生签名/架构/依赖检查必须保留。
需要内核模块时使用同次签名包或在本工作流重编译；不全量 apk upgrade 代替固件升级。

## 构建、交付及状态

工作流 `.github/workflows/rax3000m-vendor-openclash.yml` 支持 workflow_dispatch，
审核分支 `codex/rax3000m-vendor-openclash` 的相关代码 push 也可触发。
采用公共仓库标准 Ubuntu runner、contents: read、固定 Actions 提交和 2 编译线程，
不依赖作者密钥、私有服务器或通知服务，不启用付费 runner。
如手动入口要求先进入默认分支，由仓库所有者审核决定，本任务不合入或推送默认分支。

云端前置检查：

```sh
source /workspace/.kwrt-env/activate.sh
OPENWRT_MAKE=kwrt-make bash scripts/rax3000m-vendor.sh prepare BUILD_ROOT ARTIFACT_ROOT
```

GitHub Actions 使用同一 prepare，再运行 build。最终严格核对唯一设备、375 个对应项、
必要驱动/依赖/冲突、源码实际提交和补丁、Mihomo 官方二进制哈希/ARM64 架构、
默认关闭代理/小闪存模式、TAR/FIT/SquashFS/设备元数据、真实内核 ABI 和全部签名包。
失败保存日志及串行诊断，不以忽略依赖或强制接受 ABI/架构差异解决。

完整编译成功后才交付：

- `rax3000m-vendor-mihomo-firmware-<run_id>`：唯一 BIN、SHA256、最终配置/内核配置、
  完整清单、375 项映射、源码/补丁/核心版本和验收 JSON。
- `rax3000m-vendor-matching-packages-<run_id>`：同次签名 APK 和索引，仅为离线维护，另含公钥，不公开私钥。
- `rax3000m-vendor-diagnostics-<run_id>`：准备/编译/原生仓库测试日志及失败诊断，保存 30 天。

profile 没有固定 IMAGE_SIZE。最终 kernel/root 长度与初始化最低写入范围由实际镜像报告，
上限以本机 kernel/rootfs 分区为准，不能按 eMMC 总容量或“2GB”推定可写空间；不扩大分区。
旧版能启动是已知设备路径的证据，不能代替新版更大 root payload 的容量检查。
升级前私密保存配置和当前可用镜像，保留本机 factory/引导/GPT 资料；
具体备份和两种升级入口边界见原设备目录 UPGRADE.md。
APK/网页服务和应用集合均有变化，勿默认恢复整套旧系统文件；本任务不执行刷机或备份。

## 游戏延迟的对照

用户已确认：关闭 OpenClash 时正常，启用后游戏延迟升高。新软件组合是对照候选，
不能证明增加应用或内置核心会修复这类延迟。需要看游戏流量实际经过哪条路径：

1. 同一终端、同一时段、先用有线做 OpenClash 关闭/开启对照；避免其他设备大流量干扰。
2. 在连接面板查游戏相关连接的规则和最终出口，分清 DIRECT、代理节点和全局代理模式。
   国内/本地线路游戏通常先验证对应流量直连；需要跨区代理的游戏另选合适线路。
3. 节点是否支持 UDP、DNS 是否让游戏选到远端服务器、规则顺序是否把游戏误送代理，
   比新增仪表盘软件更直接影响路径。按自己的配置调整并复测，不导入公开通用节点。
4. 同时观察 CPU/内存及丢包；如果只有负载时延迟升高，再依据实际证据处理。
   不预先调整队列、加速、发射功率或重启来掩盖问题。

新镜像启动、重启/配置保留、双频/网口/USB、IPv4/运营商可用 IPv6、DNS/DHCP、
OpenClash 启停/停用恢复和至少 24～48 小时观察仍须真机验证。
配置通过、完整编译、镜像完整性和游戏低延迟是不同验收项，未验证的项目不能写为通过。
