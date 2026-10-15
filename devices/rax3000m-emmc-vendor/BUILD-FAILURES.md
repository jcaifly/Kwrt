# 构建失败与修复记录

## 运行 38588639240

- [失败运行](https://github.com/jcaifly/Kwrt/actions/runs/38588639240)，源码提交 `a5445f152173cefb3d47b6604b5d3b41bc2bd53f`。
- GitHub 公开步骤状态：配置/依赖/来源检查成功，固件编译步骤失败，镜像及软件包上传跳过，诊断上传成功。
- 原始诊断保存在该运行的 `rax3000m-vendor-diagnostics-38588639240`，构建脚本保留并行和串行日志。
  本次定位读取公开错误注释，未将需登录的完整日志声称为已经下载。

公开注释中的关键报错：

```text
aclocal.real: error: configure.ac:13: file 'tool/m4/$1' does not exist
autoreconf: error: .../staging_dir/host/bin/aclocal failed with exit status: 1
make[6]: *** [Makefile:486: Makefile.in] Error 127
make[3]: *** [.../libnftnl-1.3.1/.built] Error 2
make[2]: *** [package/Makefile:188: package/libs/libnftnl/compile] Error 1
```

FullCone 补丁修改了 libnftnl 的 `src/Makefile.am`，但原实现漏掉同一固定上游
ImmortalWrt 提交 `ce35a9e4ef1b87fbbc2146036ce6693e4242861a` 中的配套设置
`PKG_FIXUP:=autoreconf`。该设置让 OpenWrt 在 configure 前显式重生成构建文件，
避免编译时才触发旧生成文件与构建工具不匹配的自动重生成路径。

修复仅通过本设备的 `patches/libnftnl-autoreconf.patch` 应用于独立构建树。
来源检查仍逐行比对全部 OpenWrt 改动；新增这一个经过审核的配方变更，未放宽其他文件检查。
未删减商家 375 项软件对应关系，未关闭依赖、签名、下载或架构/内核 ABI 检查。

局部验证使用与固件相同的官方 libnftnl 1.3.1 源码归档，SHA256：
`607da28dba66fbdeccf8ef1395dded9077e8d19f2995f9a4d45a9c2f0bcffba8`。

- 未显式重生成时，OpenWrt SDK Automake 1.18.1 复现旧生成文件来自 Automake 1.17 的版本不匹配，退出码 2。
  这是同一自动重生成环节的复现，未声称逐字复现 Actions 的 M4 错误。
- 显式使用 OpenWrt SDK 的 autoreconf/aclocal/autoconf/automake 工具重生成成功。
- 带实际 FullCone 源码补丁的 libnftnl 在云端主机原生编译成功，包括 `expr/fullcone.o`。
- 上游 `make -j2 check`：32 项全部通过，FAIL 0、ERROR 0。

以上是主机上的构建环节验证，不等于 ARM64 完整固件编译、镜像验收或真机测试。
修复后的完整交叉编译仍交给 GitHub Actions；只有新运行全部完成才报告固件构建成功。

## 运行 38656087494

- [失败运行](https://github.com/jcaifly/Kwrt/actions/runs/38656087494)，源码提交 `d5941a5765ddee6d46da4fe4d7eb2e09fe73950d`。
- GitHub 公开步骤状态：配置和来源检查成功，固件编译步骤失败，固件与软件包上传跳过，诊断上传成功。
- 原始日志保存在 `rax3000m-vendor-diagnostics-38656087494`，本次定位依据公开错误注释。

```text
ERROR: info field 'version' has invalid value: package version is invalid
ERROR: failed to create package: package version is invalid
make[3]: *** [.../kmod-nft-fullcone-6.12.94.2023-05-17~07d93b62-r1.apk] Error 99
make[2]: *** [package/Makefile:188: package/feeds/vendor/fullconenat-nft/compile] Error 1
```

根因：本任务把固定 Git 源码改为带 SHA256 的归档下载时，自行拼接了含连字符的快照日期。
OpenWrt `include/download.mk` 的原规则会把日期中的 `-` 转成 `.`；APK 不接受日期中的这些连字符。
修复为 `6.12.94.2023.05.17~07d93b62-r1`；固定提交、源码 URL/归档 SHA256、驱动源码和真实内核 ABI 机制均保留。

同时检查全部选中版本元数据时，发现 `luci-app-fan` 的旧配方声明
`PKG_VERSION=1.0.0-r3`、`PKG_RELEASE=1`，最终拼出 `1.0.0-r3-r1`。
本设备配方分离为版本 `1.0.0` 和修订 `3`，生成可被 APK 接受的 `1.0.0-r3`；不删除风扇控制功能。
商家清单仍保留原始 `1.0.0-r3-r1` 作为历史记录，对应表明确显示新版本。

使用已验证的 OpenWrt SDK 原生 APK 3.0.2 的 `mkpkg` 实际复现：

| 版本 | 实际打包退出码 |
| --- | --- |
| `6.12.94.2023-05-17~07d93b62-r1` | 99，版本无效 |
| `6.12.94.2023.05.17~07d93b62-r1` | 0 |
| `1.0.0-r3-r1` | 99，版本无效 |
| `1.0.0-r3` | 0 |

打包测试仅使用无害文本夹具，不生成伪装为可用驱动的包，不安装任何夹具。
新增 7 项真实 APK 回归测试，覆盖上述打包、显式上游版本保留、无效内核模板后缀、
未知占位符拒绝和延迟生成的 LuCI 版本报告；全部通过。原有 7 项映射/核心完整性测试也通过。

CI 在完整交叉编译前先执行正常所需的 `tools/install` 和 `package/system/apk/host/compile`，
再使用固定 25.12.5 源码的 APK 3.0.5 做版本预检及这些回归测试；原生工具仍复用于后续 world 构建。
`package-version-check.json` 明确区分可核对的完整版本、只检查语法的模板和待生成版本。
模板探测中的数字占位仅存在于检查器内存和诊断记录，不修改真实内核版本/ABI或软件包版本。
最终包仍须通过原生 APK 创建、签名、架构和真实内核 ABI 验收；本次局部检查不代替完整编译。

## 运行 38680868400

- [失败运行](https://github.com/jcaifly/Kwrt/actions/runs/38680868400)，源码提交 `ab95dc74529012febd51a400446f1ffcdea5caab`。
- 配置/来源步骤成功，固件编译步骤失败，诊断上传成功。原始日志在 `rax3000m-vendor-diagnostics-38680868400`。
- 公开摘要中有效报错为 `configure.ac:215: error: required file 'libcork/Makefile.in' not found`。
  完整附件仍需登录；定位依据为公开注释、固定源码和云端精确复现，不声称已下载完整日志。

根因：本任务把 simple-obfs 的 Git 下载改为带 SHA256 的 codeload 归档时，遗漏了 Git 子模块。
父项目固定提交 `486bebd9208539058e57e23a12f23103016e09b4` 的 Git 树记录：

```text
160000 commit f02984545061c924808e4b9ea7cc6749a41f1979  libcork
```

修复在本设备配方中增加标准 OpenWrt Download 和 Build/Prepare 处理，将该提交的
shadowsocks/libcork 归档还原到父源码的 libcork 目录。
新增归档 SHA256 为 `0f1ede7bd23672718d1d10adbe9e4028515d029585b93092d7199e51a40b3fe4`。
原有父归档 SHA256 不改动，不取消 autoreconf，不跳过缺失文件或依赖。

实际检查：

- 使用官方 25.12.5 mediatek/filogic SDK；校验和列表的 OpenPGP 签名由已有可信 OpenWrt 公钥验证。
  SDK 归档 SHA256：`ff4a38a397caa2cfe1c39e18f84ddede14878221b3593c3f2c4cfe24e3ec4c25`。
- 仅父归档执行 SDK autoreconf，精确复现同一 `configure.ac:215` 缺失文件错误。
- 使用实际修复配方、原有 isdigit 补丁及 libev 4.33，成功交叉编译并生成
  `simple-obfs-client-0.0.5-r1.apk`；原生 APK 元数据为 aarch64_cortex-a53，暂存程序 ELF 为 64 位 ARM64（机器号 183）。
  该 SDK 组件包只用于验证，没有混入固件或当作同次固件的匹配包交付，没有执行目标程序。
- 删除本次 SDK 测试缓存中的 libcork 归档，再执行 `make package/simple-obfs/download`，实际下载钩子成功取回文件且 SHA256 匹配。
- 初次本地试验发现云端 Autotools 1.17 的环境覆盖与 SDK Autotools 1.18.1 冲突；
  在该 SDK 调用中清除这些覆盖，清理两个测试包后重建成功，初次失败日志保留。仓库配方未加入忽略该错误的逻辑。
- 检查全部三个 Git→归档替换：fullconenat-nft、tcping 无子模块；simple-obfs 只有上述 libcork，libcork 本身无下级子模块。
- 全新目录 prepare、defconfig、prereq、依赖/来源检查通过，375 项对应、446 个选中构建包、1190 条依赖和最终配置均不变。
- 9 项新增源归档/递归子模块/下载缺失/篡改/诊断回归通过；原有 7 项映射/核心测试及 7 项原生版本测试通过，后者也使用本次 SDK 的 APK 3.0.5 验证。

工作流在 make download 后运行 source-archive-check.json 检查，要求声明的全部递归子模块
已固定且归档存在、SHA256 正确、关键构建文件齐全。.gitmodules 由 Git 自身解析，正确处理其原始制表符和空格缩进。
来源报告记录父子提交和归档校验值。

旧失败摘要把编译命令中的 `-DFAILED_SLOTS_DIR` 误识别成错误，挤掉了真正原因。
现在仅匹配完整 FAILED 单词，保留真实错误和 make 失败链，摘要限制为 3000 UTF-8 字节；完整日志继续保存。

组件交叉编译通过不等于完整固件构建成功。镜像、最终包、真实内核 ABI、刷写及运行验证仍以新构建和真机结果为准。
