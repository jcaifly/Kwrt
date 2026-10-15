# SQM 候选版实际构建结果

运行：[38780611091](https://github.com/jcaifly/Kwrt/actions/runs/38780611091)，
状态 Success，总时长 3 小时 18 分 27 秒。
构建提交 `9945c6d93fffbe2bfecd7217a217167f5be6932d`，分支 `codex/rax3000m-emmc-sqm`。
此记录及首次启动说明的后续文档更正不修改该次固件，不触发新的编译。

证据为公开运行页、job `116579526407` 的各步骤成功状态及
`Verified candidate record` 注解。云端未登录的附件和分步日志下载返回 404，
因此本次复核没有独立下载 BIN 再次解包，也未读取附件内完整配置/清单/详细日志。
以下镜像检查结论来自该次 Actions 中实际执行的验收程序，不冒充云端二次验收或真机测试。

## 唯一固件镜像

`kwrt-25.12.5-sqm-mediatek-filogic-cmcc_rax3000m-emmc-squashfs-sysupgrade.bin`

- 大小：21,903,633 字节，约 21.90 MB / 20.89 MiB。
- SHA256：`b8d1cf6b969b139d11acdf56c30d4e01a1c1e19f9168945da7d9e08fa2094316`。
- 设备：CMCC RAX3000M eMMC，mediatek/filogic，cmcc_rax3000m-emmc。
- 安装包 254 个，较已用旧版增加 21 个；同次签名 APK 仓库为 254 个。
- OpenClash 0.48.002-r9；不内置 Mihomo，小闪存关闭，代理默认停用。
- Linux 内核包/实际 ABI：`6.12.94~34255bf127bd1d95b4411add83a876a3-r1`。
- SQM 已安装、队列默认关闭，上下行均为 0；启用前需要测量并配置，不会自动测速。
- HTTP/HTTPS 监听保留，不强制跳转；HTTP 明文，只适合可信 LAN。

profile 无固定 IMAGE_SIZE，真实 kernel/rootfs 分区容量及 overlay 余量仍没有本机数据。
不能用整包大小或卖家所述 2GB 代替分区容量；本次公开注解未包含 kernel/root payload 细项，
该数值应查 candidate 附件中的 artifact-check.json，不从整包大小推算。

## 自动验收与未执行项目

各步骤成功：固定来源和单设备配置准备、构建、实际镜像验收、固件上传、同次签名包上传和诊断上传。
最终 BIN 的 SquashFS 严格解包检查通过，315 个非固件 ELF 对象完成启动/动态依赖静态核对。
出厂管理配置核对到 IPv4/IPv6 HTTP 80、HTTPS 443，WAN zone 的 input=REJECT。
这些是镜像文件检查，不证明运行端口可达或完整防火墙行为。
原生包身份、签名、ABI 及离线依赖验收步骤通过；完整记录随附件交付。

首次启动、实际 eMMC/GPT、重启后配置保留、所有网口及双频 Wi-Fi、WAN 接入、
OpenClash 安装核心后的代理、SQM 效果及 24～48 小时稳定性仍待真机验证。
本版为候选固件，未将 `safe_to_flash_confirmed` 设为 true。

## 固定来源

| 组件 | 实际提交 |
| --- | --- |
| Kwrt 构建入口 | 9945c6d93fffbe2bfecd7217a217167f5be6932d |
| OpenWrt 25.12.5 | f0a60eee2fe051741c643ea6118718aae1ef17fb |
| packages | 5caa62e0bc9f7fb9b0c12a23267bceb7724214dd |
| LuCI | 128a7812f4be233c5dd7f7466f534fd888785caf |
| OpenClash 软件包源 kiddin9/op-packages | 426eda7eae561e63b6dc78f4c6bcaa4105ca4b16 |

SQM 源由上述固定 packages feed 定义：1.7.2-r1、
tohojo/sqm-scripts `20ba92639546075d8e39346dcb88a3cdfe8ee903`，
归档 SHA256 `578f7cbf5268a9f7e1689fd6365c11d8d9baebf46773237f46393088d792d8ce`。
完整来源和补丁哈希以附件 sources.json 为准。

## 下载和首次设置

登录 GitHub 后打开同次运行的 Artifacts：

- [candidate 固件包](https://github.com/jcaifly/Kwrt/actions/runs/38780611091/artifacts/12007136337)：
  BIN、SHA256SUMS、final.config、kernel.config、packages.manifest、sources.json 和检查 JSON。
- [matching-packages 同次软件包](https://github.com/jcaifly/Kwrt/actions/runs/38780611091/artifacts/12007645681)：
  匹配内核 ABI 的签名 APK、索引和公开验证密钥，不是第二份固件。
- [diagnostics 诊断包](https://github.com/jcaifly/Kwrt/actions/runs/38780611091/artifacts/12007306161)：
  编译及检查日志，不用于刷机。

保留已经成功恢复的 21.5 MB 旧镜像及本机备份，升级入口和写入范围见 UPGRADE.md。
不使用 GPT、BL2、FIP 或 U-Boot 文件作为普通升级镜像。
首次用网线连接 LAN，在 `http://192.168.1.1` 或 HTTPS 登录，设置强 root 密码。
该镜像首次脚本执行时，即使保留旧配置，也会关闭无线、OpenClash 和 SQM，
取消 HTTPS 强制跳转；旧接口/速率/代理规则可能保留，需要重新核对。
无线需设置监管域、SSID 和强密码后启用；OpenClash 保持小闪存关闭，手动安装并校验 ARM64 核心。
基础网络正常后再做代理和 SQM 对照，参照 BUILD-REVIEW.md。
