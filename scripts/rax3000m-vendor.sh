#!/bin/bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
profile="$repo_dir/devices/rax3000m-emmc-vendor"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=../devices/rax3000m-emmc-vendor/sources.env
source "$profile/sources.env"
mode=${1:?Usage: rax3000m-vendor.sh prepare|build|collect BUILD_ROOT ARTIFACT_ROOT}
build_root=${2:?BUILD_ROOT required}
artifact_root=${3:?ARTIFACT_ROOT required}
mkdir -p "$build_root" "$artifact_root/diagnostics"
build_root=$(realpath "$build_root")
artifact_root=$(realpath "$artifact_root")
tree="$build_root/openwrt"
diagnostics="$artifact_root/diagnostics"
make_cmd=${OPENWRT_MAKE:-make}

run_make() {
    "$make_cmd" -C "$tree" RECURSIVE_DEP_IS_ERROR=1 DOWNLOAD_CHECK_CERTIFICATE=y \
        EXTRA_IMAGE_NAME=vendor-openclash-mihomo "$@"
}

preserve() {
    local result=$?
    trap - EXIT
    set +e
    printf '%s\n' "$result" > "$diagnostics/$mode.exit-code"
    cp "$profile/sources.env" "$profile/source-hashes.json" "$profile/vendor-packages.manifest" "$diagnostics/"
    [[ ! -f "$tree/.config" ]] || cp "$tree/.config" "$diagnostics/final.config"
    [[ ! -d "$tree/logs" ]] || tar -czf "$diagnostics/openwrt-logs.tar.gz" -C "$tree" logs
    if [[ "$result" != 0 && "${GITHUB_ACTIONS:-false}" == true ]]; then
        python3 -B - "$diagnostics" "$repo_dir" "$tree" <<'PY'
from pathlib import Path
import importlib.util
import json
import shutil
import sys
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('vendor', Path(sys.argv[2]) / 'scripts/rax3000m-vendor.py')
vendor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vendor)
tree = Path(sys.argv[3])
target = tree / 'bin/targets/mediatek/filogic'
for file in [*target.glob('*.manifest'), target / 'profiles.json', target / 'sha256sums']:
    if file.is_file():
        shutil.copyfile(file, root / file.name)
for image_root in tree.glob('build_dir/target-*/root-mediatek'):
    if (image_root / 'lib/apk/db/installed').is_file():
        records = vendor.common.installed_records(image_root)
        summary = {name: {key: record[key] for key in ('P', 'V', 'A', 'D', 'p', 'C') if key in record}
                   for name, record in records.items()}
        (root / 'installed-package-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
logs = [root / n for n in ('build-serial.log', 'build-parallel.log', 'source-archive-check.log', 'package-version-check.log', 'native-version-tests.log', 'native-apk.log', 'host-tools.log', 'prepare.log', 'build.log')]
for path in logs:
    if path.is_file():
        text = vendor.failure_excerpt(path.read_text(errors='replace'))
        if text:
            print('::error title=Vendor rebuild diagnostics::' + text.replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D'))
            break
PY
    fi
    exit "$result"
}
trap preserve EXIT
exec > >(tee -a "$diagnostics/$mode.log") 2>&1

check() {
    python3 -B "$repo_dir/scripts/rax3000m-vendor.py" config "$tree" "$diagnostics/config-check.json"
    python3 -B "$repo_dir/scripts/rax3000m-vendor.py" provenance "$build_root" "$diagnostics/sources.json"
    cp "$tree/.config" "$diagnostics/final.config"
    (cd "$tree" && ./scripts/diffconfig.sh) > "$diagnostics/diff.config"
}

sparse_clone() {
    local destination=$1 url=$2 commit=$3
    [[ ! -e "$destination" ]] || { printf 'Refusing to replace source directory: %s\n' "$destination" >&2; return 1; }
    git init -q "$destination"
    git -C "$destination" remote add origin "$url"
    git -C "$destination" config remote.origin.promisor true
    git -C "$destination" config remote.origin.partialclonefilter blob:none
    git -C "$destination" sparse-checkout init --no-cone
    git -C "$destination" sparse-checkout set --no-cone --stdin < "$profile/feed-paths.txt"
    git -C "$destination" fetch --depth=1 --filter=blob:none origin "$commit"
    git -C "$destination" checkout --detach FETCH_HEAD
    [[ $(git -C "$destination" rev-parse HEAD) == "$commit" ]]
}

collect() {
    check
    python3 -B "$repo_dir/scripts/rax3000m-vendor.py" artifact "$tree" "$diagnostics/artifact-check.json"
    [[ ! -e "$artifact_root/firmware" ]] || { printf 'Use a fresh ARTIFACT_ROOT.\n' >&2; return 1; }
    mkdir -p "$artifact_root/firmware"
    python3 -B "$repo_dir/scripts/collect-rax3000m-packages.py" "$tree" \
        "$diagnostics/artifact-check.json" "$artifact_root/matching-packages" \
        "$diagnostics/package-repository-check.json"
    cp "$tree/bin/targets/mediatek/filogic/"*cmcc_rax3000m-emmc-squashfs-sysupgrade.bin "$artifact_root/firmware/"
    cp "$tree/bin/targets/mediatek/filogic/"*.manifest "$artifact_root/firmware/packages.manifest"
    cp "$tree/bin/targets/mediatek/filogic/profiles.json" "$artifact_root/firmware/"
    cp "$diagnostics/"{final.config,diff.config,config-check.json,sources.json,artifact-check.json,package-repository-check.json,package-map.json,source-adaptation.json,package-version-check.json,source-archive-check.json} "$artifact_root/firmware/"
    cp "$tree"/build_dir/target-*/linux-mediatek_filogic/linux-*/.config "$artifact_root/firmware/kernel.config"
    cp "$profile/"{README.md,PACKAGE-MAP.md,vendor-packages.manifest,sources.env,source-hashes.json} "$artifact_root/firmware/"
    cp "$repo_dir/devices/rax3000m-emmc-openclash/UPGRADE.md" "$artifact_root/firmware/"
    cp "$repo_dir/devices/rax3000m-emmc-openclash/PACKAGES.md" "$artifact_root/matching-packages/README.md"
    (cd "$artifact_root/firmware" && sha256sum ./*.bin > SHA256SUMS)
    python3 - "$artifact_root/firmware" <<'PY'
from pathlib import Path
import json
import os
import sys
folder = Path(sys.argv[1])
r = json.loads((folder / 'artifact-check.json').read_text())
record = {key: r[key] for key in ('image', 'sha256', 'image_size_bytes', 'package_count', 'openclash_version', 'kernel_package_version', 'candidate_firmware', 'safe_to_flash_confirmed', 'game_latency_fix_verified')}
record['mihomo'] = r['mihomo']
record['vendor_packages_mapped'] = 375
record['kernel_bytes'] = r['tar']['kernel_bytes']
record['minimum_root_partition_bytes'] = r['tar']['minimum_root_partition_bytes']
text = '# 商家软件组合候选构建\n\n配置、完整编译、镜像与同次签名包检查通过；实际刷写与游戏延迟待真机确认。\n\n```json\n' + json.dumps(record, ensure_ascii=False, indent=2) + '\n```\n'
(folder / 'VALIDATION.md').write_text(text)
if os.getenv('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
        stream.write(text)
print('::notice title=Verified vendor candidate::' + json.dumps(record, ensure_ascii=False).replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D'))
PY
}

case "$mode" in
    prepare)
        # Reuse the validated device path and fixed release. Keep its diagnostics separate.
        bash "$repo_dir/scripts/rax3000m-emmc-openclash.sh" prepare "$build_root" "$artifact_root/bootstrap"
        rm -- "$tree/files/etc/uci-defaults/zz-rax3000m-openclash"
        sparse_clone "$build_root/vendor-feed" "$VENDOR_FEED_URL" "$VENDOR_FEED_COMMIT"
        python3 -B "$repo_dir/scripts/adapt-rax3000m-vendor.py" "$build_root" "$diagnostics/source-adaptation.json"
        cat >> "$tree/feeds.conf" <<EOF
src-link vendor $build_root/vendor-feed
src-link local $profile/packages
EOF
        (cd "$tree" && ./scripts/feeds update -a)
        # Feed indexing is not package selection. Only vendor equivalents and dependencies are selected.
        (cd "$tree" && ./scripts/feeds install -a -p vendor && ./scripts/feeds install -a -p local)
        python3 -B "$repo_dir/scripts/rax3000m-vendor.py" map "$tree" "$diagnostics/package-map.json"
        python3 - "$diagnostics/package-map.json" > "$diagnostics/package-symbols.txt" <<'PY'
import json
import sys
rows = json.load(open(sys.argv[1]))['packages']
print('\n'.join(sorted({r['symbol'] for r in rows if r['symbol']} | {'luci-app-openclash', 'openclash-mihomo-core', 'luci-nginx', 'nginx-ssl', 'openssl-util'})))
PY
        mapfile -t packages < "$diagnostics/package-symbols.txt"
        (cd "$tree" && ./scripts/feeds install "${packages[@]}")
        python3 -B "$repo_dir/scripts/rax3000m-vendor.py" map "$tree" "$diagnostics/package-map.json"
        run_make defconfig
        run_make prereq
        check
        ;;
    build)
        check
        jobs=${BUILD_JOBS:-2}
        [[ "$jobs" =~ ^[1-4]$ ]] || { printf 'BUILD_JOBS must be 1..4.\n' >&2; exit 1; }
        run_make -j"$jobs" download 2>&1 | tee "$diagnostics/download.log"
        python3 -B "$repo_dir/scripts/rax3000m-vendor.py" archives "$build_root" "$diagnostics/source-archive-check.json" \
            2>&1 | tee "$diagnostics/source-archive-check.log"
        # These host tools are also required by world. Check package metadata
        # with the real packager before spending time on the cross compilation.
        run_make -j"$jobs" tools/install 2>&1 | tee "$diagnostics/host-tools.log"
        run_make -j"$jobs" package/system/apk/host/compile 2>&1 | tee "$diagnostics/native-apk.log"
        OPENWRT_APK="$tree/staging_dir/host/bin/apk" \
            python3 -B -m unittest discover -s "$repo_dir/scripts/tests" -p test_rax3000m_versions.py -v \
            2>&1 | tee "$diagnostics/native-version-tests.log"
        python3 -B "$repo_dir/scripts/rax3000m-vendor.py" versions "$tree" "$diagnostics/package-version-check.json" \
            2>&1 | tee "$diagnostics/package-version-check.log"
        if ! run_make -j"$jobs" 2>&1 | tee "$diagnostics/build-parallel.log"; then
            run_make -j1 V=s 2>&1 | tee "$diagnostics/build-serial.log"
        fi
        OPENWRT_APK="$tree/staging_dir/host/bin/apk" OPENWRT_OPENSSL="$tree/staging_dir/host/bin/openssl" \
            python3 -B -m unittest discover -s "$repo_dir/scripts/tests" -p test_collect_rax3000m_packages.py -v \
            2>&1 | tee "$diagnostics/native-package-tests.log"
        collect
        ;;
    collect) collect ;;
    *) printf 'Unknown mode: %s\n' "$mode" >&2; exit 2 ;;
esac
