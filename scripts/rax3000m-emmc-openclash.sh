#!/bin/bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
profile_dir="$repo_dir/devices/rax3000m-emmc-openclash"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=../devices/rax3000m-emmc-openclash/sources.env
source "$profile_dir/sources.env"
mode=${1:?Usage: rax3000m-emmc-openclash.sh prepare|build|collect BUILD_ROOT ARTIFACT_ROOT}
build_root=${2:?BUILD_ROOT required}
artifact_root=${3:?ARTIFACT_ROOT required}
mkdir -p "$build_root" "$artifact_root/diagnostics"
build_root=$(realpath "$build_root")
artifact_root=$(realpath "$artifact_root")
tree="$build_root/openwrt"
openclash_feed="$build_root/openclash-feed"
diagnostics="$artifact_root/diagnostics"
make_cmd=${OPENWRT_MAKE:-make}

run_make() {
    "$make_cmd" -C "$tree" RECURSIVE_DEP_IS_ERROR=1 DOWNLOAD_CHECK_CERTIFICATE=y "$@"
}

preserve_diagnostics() {
    local result=$?
    trap - EXIT
    set +e
    printf '%s\n' "$result" > "$diagnostics/$mode.exit-code"
    cp "$profile_dir/sources.env" "$diagnostics/source-pins.env"
    cp "$profile_dir/patches/kwrt-emmc-layout.patch" "$diagnostics/"
    [[ ! -f "$tree/.config" ]] || cp "$tree/.config" "$diagnostics/final.config"
    [[ ! -d "$tree/logs" ]] || tar -czf "$diagnostics/openwrt-logs.tar.gz" -C "$tree" logs
    if [[ -d "$tree/target/linux/mediatek" ]]; then
        mkdir -p "$diagnostics/upstream-upgrade"
        cp "$tree/target/linux/mediatek/filogic/base-files/lib/upgrade/platform.sh" \
            "$tree/package/base-files/files/lib/upgrade/emmc.sh" \
            "$tree/package/utils/fitblk/files/fit.sh" \
            "$tree/package/base-files/files/lib/upgrade/fwtool.sh" \
            "$tree/package/base-files/files/sbin/sysupgrade" "$diagnostics/upstream-upgrade/"
        [[ ! -f "$tree/target/linux/mediatek/filogic/base-files/lib/upgrade/rax3000m-emmc.sh" ]] || \
            cp "$tree/target/linux/mediatek/filogic/base-files/lib/upgrade/rax3000m-emmc.sh" \
                "$diagnostics/upstream-upgrade/"
    fi
    df -h > "$diagnostics/disk-usage.txt"
    if [[ "$result" != 0 && "${GITHUB_ACTIONS:-false}" == true ]]; then
        python3 - "$diagnostics" "$mode" <<'PY'
import os
from pathlib import Path
import re
import sys

directory = Path(sys.argv[1])
logs = [directory / name for name in ('build-serial.log', 'build-parallel.log', 'download.log', sys.argv[2] + '.log')]
log = next((path for path in logs if path.is_file()), None)
if log:
    lines = log.read_text(errors='replace').splitlines()
    errors = [line for line in lines if re.search(r'error:|FAILED:|Error [0-9]|^ERROR:|No rule to make', line)]
    detail = '\n'.join(errors[-12:] + lines[-8:])[-12000:]
    detail = detail.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=RAX3000M build diagnostics::' + detail, flush=True)
PY
    fi
    exit "$result"
}
trap preserve_diagnostics EXIT
exec > >(tee -a "$diagnostics/$mode.log") 2>&1

clone_exact() {
    local url=$1 commit=$2 destination=$3
    [[ ! -e "$destination" ]] || {
        printf 'Refusing to overwrite existing sources: %s\n' "$destination" >&2
        return 1
    }
    git init -q "$destination"
    git -C "$destination" remote add origin "$url"
    git -C "$destination" fetch --depth=1 origin "$commit"
    git -C "$destination" checkout --detach FETCH_HEAD
    [[ $(git -C "$destination" rev-parse HEAD) == "$commit" ]]
}

check_config() {
    python3 "$repo_dir/scripts/check-rax3000m.py" config "$tree" "$diagnostics/config-check.json"
    cp "$tree/.config" "$diagnostics/final.config"
    (cd "$tree" && ./scripts/diffconfig.sh) > "$diagnostics/diff.config"
    python3 "$repo_dir/scripts/check-rax3000m.py" provenance \
        "$repo_dir" "$build_root" "$diagnostics/sources.json"
}

collect() {
    check_config
    python3 "$repo_dir/scripts/check-rax3000m.py" artifact "$tree" "$diagnostics/artifact-check.json"
    [[ ! -e "$artifact_root/firmware" ]] || {
        printf 'Refusing to mix firmware with previous artifacts; use a new ARTIFACT_ROOT.\n' >&2
        return 1
    }
    mkdir -p "$artifact_root/firmware"
    local target_dir="$tree/bin/targets/mediatek/filogic"
    # Only the native kernel/rootfs TAR image; no GPT or bootloader artifacts.
    cp "$target_dir/"*cmcc_rax3000m-emmc-squashfs-sysupgrade.bin "$artifact_root/firmware/"
    cp "$target_dir/"*.manifest "$artifact_root/firmware/packages.manifest"
    cp "$target_dir/profiles.json" "$artifact_root/firmware/"
    cp "$diagnostics/final.config" "$diagnostics/diff.config" \
        "$diagnostics/sources.json" "$diagnostics/config-check.json" \
        "$diagnostics/artifact-check.json" "$artifact_root/firmware/"
    cp "$tree"/build_dir/target-*/linux-mediatek_filogic/linux-*/.config \
        "$artifact_root/firmware/kernel.config"
    cp "$profile_dir/README.md" "$profile_dir/UPGRADE.md" "$profile_dir/VALIDATION.md" \
        "$profile_dir/VENDOR-FIRMWARE.md" \
        "$profile_dir/collect-device-info.sh" "$artifact_root/firmware/"
    python3 - "$artifact_root/firmware" "$mode" <<'PY'
import json
from pathlib import Path
import sys

folder = Path(sys.argv[1])
report = json.loads((folder / 'artifact-check.json').read_text())
sources = json.loads((folder / 'sources.json').read_text())
lines = [
    '# 本次候选固件验证', '',
    '候选固件；尚未确认可刷写。真机及代理运行均未验证。', '',
    '| 项目 | 实际结果 |', '| --- | --- |',
    f"| 完整编译 | {'本次 build 命令成功' if sys.argv[2] == 'build' else 'collect 模式，请结合对应编译日志判断'} |",
    '| 配置 / 来源 / 镜像文件检查 | 通过 |',
    f"| 镜像 | `{report['image']}` |",
    f"| SHA256 | `{report['sha256']}` |",
    f"| 镜像大小 | {report['image_size_bytes']} 字节 |",
    '| 允许上限 | 该独立 eMMC profile 无固定 IMAGE_SIZE；实际 kernel/rootfs 分区容量待采集 |',
    f"| kernel / root 最低所需空间 | {report['tar']['kernel_bytes']} / {report['tar']['minimum_root_partition_bytes']} 字节；后者仅含初始化标记，不代表足够可写空间 |",
    '| 实机 GPT / U-Boot / sysupgrade -T / 硬件和长期运行 | 待验证 |',
    f"| 最终安装包数 / OpenClash | {report['package_count']} / {report['openclash_version']} |",
    f"| Linux 内核包 / ABI | `{report['kernel_package_version']}` |",
    '| Mihomo / 默认代理 / 小闪存模式 | 未预装 / 停用 / 关闭 |', '',
    '| 来源 | 实际提交 |', '| --- | --- |',
]
for name in ('kwrt', 'openwrt', 'packages', 'luci', 'openclash'):
    lines.append(f"| {name} | `{sources[name]['commit']}` |")
lines.extend(['', '包清单、源码及详细检查见同包 JSON/config/manifest。',
              '升级前读取 UPGRADE.md。仅 cmcc_rax3000m-emmc 的 sysupgrade.bin 是候选普通升级对象；不刷 GPT、BL2、FIP。',
              '同次运行的 diagnostics 附件保存编译及失败诊断日志。', ''])
(folder / 'VALIDATION.md').write_text('\n'.join(lines))
PY
    (cd "$artifact_root/firmware" && sha256sum ./*.bin > SHA256SUMS)
    cat "$artifact_root/firmware/SHA256SUMS"
}

case "$mode" in
    prepare)
        clone_exact "$OPENWRT_URL" "$OPENWRT_COMMIT" "$tree"
        git -C "$tree" apply --check --index --unidiff-zero "$profile_dir/patches/kwrt-emmc-layout.patch"
        git -C "$tree" apply --index --unidiff-zero "$profile_dir/patches/kwrt-emmc-layout.patch"
        [[ ! -e "$openclash_feed" ]]
        git init -q "$openclash_feed"
        git -C "$openclash_feed" remote add origin "$OPENCLASH_URL"
        git -C "$openclash_feed" config remote.origin.promisor true
        git -C "$openclash_feed" config remote.origin.partialclonefilter blob:none
        git -C "$openclash_feed" sparse-checkout init --no-cone
        git -C "$openclash_feed" sparse-checkout set --no-cone /luci-app-openclash/
        git -C "$openclash_feed" fetch --depth=1 --filter=blob:none origin "$OPENCLASH_COMMIT" \
            2>&1 | tee "$diagnostics/openclash-fetch.log"
        if rg -q 'filtering not recognized|does not support filter' "$diagnostics/openclash-fetch.log"; then
            printf 'Partial clone is required; refusing to download other feed packages or cores.\n' >&2
            exit 1
        fi
        git -C "$openclash_feed" checkout --detach FETCH_HEAD
        [[ $(git -C "$openclash_feed" rev-parse HEAD) == "$OPENCLASH_COMMIT" ]]
        patch --batch --fuzz=0 -p1 -d "$openclash_feed" < "$profile_dir/patches/openclash-host-build.patch"
        patch --batch --fuzz=0 -p1 -d "$openclash_feed" < "$profile_dir/patches/openclash-apk-verification.patch"
        cat > "$tree/feeds.conf" <<EOF
src-git packages $PACKAGES_URL^$PACKAGES_COMMIT
src-git luci $LUCI_URL^$LUCI_COMMIT
src-link openclash $openclash_feed
EOF
        cp "$profile_dir/config" "$tree/.config"
        cp -a "$profile_dir/files" "$tree/files"
        chmod 0755 "$tree/files/etc/uci-defaults/zz-rax3000m-openclash"
        (cd "$tree" && ./scripts/feeds update -a)
        (cd "$tree" && ./scripts/feeds install \
            luci-light luci-ssl luci-compat luci-lib-ipkg luci-app-package-manager luci-app-openclash)
        [[ $(git -C "$tree/feeds/packages" rev-parse HEAD) == "$PACKAGES_COMMIT" ]]
        [[ $(git -C "$tree/feeds/luci" rev-parse HEAD) == "$LUCI_COMMIT" ]]
        cp "$profile_dir/config" "$tree/.config"
        run_make defconfig
        run_make prereq
        check_config
        ;;
    build)
        check_config
        build_jobs=${BUILD_JOBS:-2}
        [[ "$build_jobs" =~ ^[1-4]$ ]] || { printf 'BUILD_JOBS must be 1..4\n' >&2; exit 1; }
        run_make -j"$build_jobs" download 2>&1 | tee "$diagnostics/download.log"
        if ! run_make -j"$build_jobs" 2>&1 | tee "$diagnostics/build-parallel.log"; then
            run_make -j1 V=s 2>&1 | tee "$diagnostics/build-serial.log"
        fi
        collect
        ;;
    collect) collect ;;
    *) printf 'Unknown mode: %s\n' "$mode" >&2; exit 2 ;;
esac
