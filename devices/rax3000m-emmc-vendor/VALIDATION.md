# 本次前置检查

配置/工作流已准备；新版固件尚未完成完整编译，游戏延迟改善未验证。

- 从全新目录执行 scripts/rax3000m-vendor.sh prepare，退出码 0。
- 实际 make defconfig / prereq 通过；唯一 cmcc_rax3000m-emmc / mediatek/filogic / aarch64_cortex-a53。
- 商家 375 项全部有明确对应，446 个构建包、1190 条运行依赖；无独立 m 包，无 SDK/ImageBuilder/全设备或全包选择。
- 依赖提供者和冲突检查通过；源码固定提交与明确适配文件哈希检查通过。
- 最终配置 SHA256：5d776e22d71a5ffb5191176ef09b6d2a5663b2290022219740ec0c892cec4977。这是配置哈希，不是固件哈希。
- 7 项映射/完整性/错误架构/载荷篡改回归测试通过；实际官方 Mihomo ARM64 文件另通过 SHA256 和 ELF 检查。
- quickstart、chinadns-ng 实际选用文件均为 AArch64；9 个下载的源码/二进制 SHA256 与固定清单一致。
- actionlint、ShellCheck、Python 语法及 git diff --check 通过。
- 首次严格 defconfig 检出 Passwall 自依赖选项和 sing-box-tiny 的递归依赖；已按完整客户集合/full 包修复，未关闭检查，原始日志保留。
- 完整新目录 prepare 复现同一 375 项映射和全部 446 个选中包。旧检查树多出未启用的 v2ray/xray 注释行，原始配置哈希因此不同；未把旧哈希当成最终配置哈希。

尚未完成：完整交叉编译、FullCone 支持补丁在全部目标源码上的编译、最终镜像/软件包签名验收、实际镜像大小和 SHA256、真机及代理/游戏测试。
构建成功才发布新版 BIN 和实际结果；本记录不代替最终 manifest 或完整编译。
原 20.52 MiB 版本已由用户刷入、能够管理和正常直连，启用 OpenClash 后游戏延迟升高；这不是新版验收通过。
