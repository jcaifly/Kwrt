# 验证记录

当前阶段：独立配置、工作流及最终前置检查通过，准备提交审核分支并执行验证构建。
此源码记录写入时完整固件尚未构建。构建附件中的 VALIDATION.md 会由实际镜像检查结果生成，
不把源码里的前置状态当作最终产物结论。任何合成测试均不代表真机运行结果。

## 已取得的证据

- 云环境现有仓库为 `jcaifly/Kwrt`，默认分支 `25.12`，开始时提交
  `67653046240b4c29faab12e8814102992d88c6d1`，工作区干净。
- 本次独立审核分支为 `codex/rax3000m-emmc-openclash`，不推送/合并默认分支。
- 官方可见最新 25.12 稳定标签为 v25.12.5，提交 `f0a60eee2fe051741c643ea6118718aae1ef17fb`。
- 设备定义为统一 `cmcc_rax3000m`，包含正式 NAND/eMMC DT overlay。
- eMMC overlay 引用 `production` 和 `factory`；升级使用 FIT/rootdisk 路径。
- 当前设备资料仅有用户转述：Kwrt、yuzhuii U-Boot、卖家调整约 2GB 软件分区。
  没有直接连接路由器，也没有实际分区/启动证据。

## 前置命令

```sh
make defconfig
make prereq
python3 -B scripts/check-rax3000m.py config OPENWRT_DIR config-check.json
python3 -B scripts/check-rax3000m.py provenance KWRT_DIR BUILD_ROOT sources.json
python3 -B -m unittest discover -s scripts/tests -p test_check_rax3000m.py -v
actionlint -shellcheck= .github/workflows/rax3000m-emmc-openclash.yml
shellcheck -x scripts/rax3000m-emmc-openclash.sh \
  devices/rax3000m-emmc-openclash/collect-device-info.sh \
  devices/rax3000m-emmc-openclash/files/etc/uci-defaults/zz-rax3000m-openclash
```

云环境以现有 `kwrt-make` 工具封装执行 make，启用真实依赖错误及 HTTPS 证书检查；
GitHub Actions 使用原生 make。最终实际命令、结果和配置随诊断产物保存。
最终 prepare 命令在新目录真实执行，退出码 0：

```sh
source /workspace/.kwrt-env/activate.sh
OPENWRT_MAKE=kwrt-make bash scripts/rax3000m-emmc-openclash.sh prepare \
  /workspace/scratch/rax3000m-build-final /workspace/scratch/rax3000m-artifacts-final
```

选中唯一 `TARGET_mediatek_filogic_DEVICE_cmcc_rax3000m`，架构 `aarch64_cortex-a53`，
235 个选中包（包含上游 profile 的引导构建依赖，不能据此当作实际安装包数），
592 条运行依赖检查通过，无独立 m 软件包，无排除应用/核心，未启用 SDK/ImageBuilder。
最终 .config SHA256 为 `4b6afb5c5fdf09573f95c4543788cb8162234f26307cd61c5489783b7b541960`，
**这是配置哈希，不是固件哈希**。
`CONFIG_FEED_openclash=n` 仅排除不存在的官方 OpenClash 软件源，插件保留。
两项本地补丁均零 fuzz 应用，来源/局部对象审计通过，未取其他 feed 软件包 blob 或核心。

11 项 FIT 格式/校验/越界/架构、核心排除和包依赖回归测试通过。
11 个真实配置负例（额外设备、批量、SDK、DNS 冲突、缺无线/IPv6、额外应用/核心、
关闭签名、错误 feed 和错误架构）均被拒绝；原配置恢复后再次通过。
actionlint 1.7.11、ShellCheck 0.10.0（`-x`）、bash/sh 语法及 Python/内嵌脚本语法通过。
APK 自更新的签名/覆盖绕过已通过本设备补丁去除，核心上传/更新脚本未修改。
固定 mt76 `39c960c3ada558b4c2e7915772483d3731573d09` 的 `mt7915/mmio.c`
中 `static bool wed_enable;` 默认 false；内核支持保留，不额外启用。

工作流检查设备唯一性、基础服务/驱动、592 条运行依赖、冲突、排除包、来源及无核心下载。
镜像阶段进一步检查 FIT 各 payload 校验、DT/overlay、squashfs、fwtool 元数据、
尺寸、最终 manifest/APK 数据库、ARM64 ELF、内核 ABI、中文资源及安全默认脚本。

## 必须分开的状态

| 项目 | 状态 / 来源 |
| --- | --- |
| 源码设备/升级分析 | 已完成，固定版本源码 |
| 配置检查 | 最终配置通过，真实 make defconfig/prereq、592 条依赖及 11 负例 |
| 工作流及回归检查 | 语法/静态检查通过，11 回归测试通过 |
| 完整固件编译 | 尚未执行 |
| 最终镜像完整性/大小 | 待实际产物检查，当前无镜像或 SHA256 |
| 当前系统预检查 | 待用户提供只读资料；未执行 sysupgrade -T |
| 引导/GPT/升级写入兼容 | 待验证，不按卖家 2GB 描述认定 |
| 真机启动、双频、网口、上网、USB、重启、24～48h | 待验证 |
| 手动核心安装后的 OpenClash/停用恢复 | 待验证，未安装 Mihomo |

GitHub API 在本云环境返回 `Forbidden`，不因此请求用户把 Token 发到聊天。
HTTPS Git 已证明可读取默认分支；分支推送/工作流触发及公开运行页面的可读性另行记录。
如无手动入口，由用户审核后决定是否让工作流进入默认分支，本任务不代为合入。
