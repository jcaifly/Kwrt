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
