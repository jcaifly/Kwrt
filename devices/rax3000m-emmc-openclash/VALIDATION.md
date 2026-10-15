# SQM 候选版验证记录

本版从已用基线提交 `3df480802ab87cf999c6508d8f462b10c3cbe146` 派生。
旧版成功刷入及恢复是用户反馈；新增 SQM 候选版的完整编译、镜像和真机结果须分别取得。
选择理由、基线 SHA256 和游戏对照步骤见 [BUILD-REVIEW.md](BUILD-REVIEW.md)。

| 项目 | 当前证据与状态 |
| --- | --- |
| 全新源码 prepare / defconfig / prereq | 已通过，未跳过编译依赖检查 |
| 设备选择 | 唯一 mediatek/filogic / cmcc_rax3000m-emmc / aarch64_cortex-a53 |
| 依赖闭包 | 260 个构建包、651 条运行依赖边；无独立 m 包、Mihomo、其他额外应用、SDK/ImageBuilder |
| 与旧版配置差异 | 不删除旧版已选包；增加 21 个 SQM 及其依赖选择（构建选择数不是最终安装数） |
| 默认配置 | OpenClash 与 SQM 停用，小闪存关闭，SQM 速率 0，HTTP/HTTPS 保留且不强制跳转 |
| 基线真实镜像严格提取 | 已通过，排除 dev/console；退出码 0、stderr 空，无其他设备节点 |
| 基线启动文件与动态库 | 静态检查通过：5 个基础服务、12 个程序路径、248 个 ELF、581 条依赖边 |
| 新候选完整编译 / 镜像大小 / 最终包数 / ABI | 待本次 Actions 结果，不引用旧版数值冒充 |
| 首次启动 / 当前系统预检查 / 具体 GPT 边界 | 待验证 |
| 新候选 U-Boot 实刷及基础网络 | 待验证；旧版恢复成功不代替本版结果 |
| SQM 与 OpenClash 游戏延迟 / 长期稳定性 | 待真机对照及 24～48 小时观察 |

本次云端最终配置 SHA256：
`12aad48d6aee9ce3fafdaf464dc69aea6effc9c0d06488423854d5f08328e646`。
云端诊断位于 `/workspace/scratch/rax3000m-sqm-artifacts/diagnostics`；
完整编译后以 Actions 交付的 final.config 和检查结果为准。
未选包的 libpam/libtirpc/libnetsnmp 等元数据警告仍记录在 prepare 日志中，
所选包的实际依赖闭包检查通过；不忽略任何所选依赖缺失。

## 实际检查入口

```sh
source /workspace/.kwrt-env/activate.sh
OPENWRT_MAKE=/workspace/.kwrt-env/bin/kwrt-make \
  bash scripts/rax3000m-emmc-openclash.sh prepare \
  /workspace/scratch/rax3000m-sqm-build /workspace/scratch/rax3000m-sqm-artifacts
```

prepare 已执行真实 defconfig、target/linux/prereq、配置与来源补丁检查。
云端回归使用已核对的 SDK host APK 3.0.5/OpenSSL 和 SquashFS 4.7.4 工具，
只生成临时测试数据，不将 SDK 软件包混入固件。79 项测试全部通过，无跳过；
actionlint（新、旧两份 workflow）、ShellCheck、Python AST、git diff --check 均通过。
SQM 原生源码下载目标通过，归档 SHA256 与固定 feed 的 PKG_MIRROR_HASH 一致。
原生测试验证单包签名、索引、身份、架构、内核 ABI 和离线依赖；
不执行目标软件包脚本，不强装依赖或关闭签名。
新增原生 SquashFS 测试覆盖正常镜像、截断损坏、非预期设备节点及归档成员错误。
新增启动检查覆盖关键服务链接、解释器、动态库闭包、路径逃逸及 DHCP 默认配置。

Actions 编译完成后再次用同次原生工具运行签名仓库和 SquashFS 测试，
对实际交付 BIN 严格提取并校验，然后生成 firmware/VALIDATION.md 与检查 JSON。
失败日志也保留。新镜像不会因旧版通过、合成测试通过或 SHA256 一致而被标为真机通过。

## 不变的兼容性边界

固定上游稳定 v25.12.5、发行版 feeds 和 OpenClash，来源见 sources.env / sources.json。
保留 Kwrt eMMC kernel/rootfs TAR 布局、共用设备树及官方 NAND/eMMC 支持；
不写 GPT、BL2、FIP、U-Boot、factory，不修改分区容量或加入自动扩容。
实际 kernel/rootfs 分区上限及 overlay 可写空间仍需本机数据，不能用卖家所述 2GB 推算。
升级、备份和恢复边界见 UPGRADE.md；本任务不自动连接、读取或刷写用户路由器。

基础网络和代理测试分阶段执行。QQ 飞车优先对照直连与规则模式，Steam 按游戏服务器区分；
开后台页面改善延迟尚未证实原因，不增加 CPU 性能强制、轮询保活或定时重启。
SQM 仅用于实测证实的出口拥塞，不是代理线路质量保证。
