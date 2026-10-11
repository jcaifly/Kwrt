#!/bin/bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
profile_dir="$repo_dir/devices/newifi-d2-openclash"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=../devices/newifi-d2-openclash/sources.env
source "$profile_dir/sources.env"
mode=${1:?Usage: newifi-d2-openclash.sh prepare|build|collect BUILD_ROOT ARTIFACT_ROOT}
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
    if [[ -f "$tree/.config" ]]; then
        cp "$tree/.config" "$diagnostics/final.config"
    fi
    if [[ -d "$tree/logs" ]]; then
        tar -czf "$diagnostics/openwrt-logs.tar.gz" -C "$tree" logs
    fi
    df -h > "$diagnostics/disk-usage.txt"
    exit "$result"
}
trap preserve_diagnostics EXIT
exec > >(tee -a "$diagnostics/$mode.log") 2>&1

clone_exact() {
    local url=$1 commit=$2 destination=$3
    [[ ! -e "$destination" ]] || {
        printf 'Refusing to overwrite existing source directory: %s\n' "$destination" >&2
        return 1
    }
    git init -q "$destination"
    git -C "$destination" remote add origin "$url"
    git -C "$destination" fetch --depth=1 origin "$commit"
    git -C "$destination" checkout --detach FETCH_HEAD
    [[ $(git -C "$destination" rev-parse HEAD) == "$commit" ]]
}

record_sources() {
    python3 "$repo_dir/scripts/check-newifi-d2.py" provenance \
        "$repo_dir" "$build_root" "$diagnostics/sources.json"
}

check_config() {
    python3 "$repo_dir/scripts/check-newifi-d2.py" config \
        "$tree" "$diagnostics/config-check.json"
    cp "$tree/.config" "$diagnostics/final.config"
    (cd "$tree" && ./scripts/diffconfig.sh) > "$diagnostics/diff.config"
    record_sources
}

collect() {
    check_config
    python3 "$repo_dir/scripts/check-newifi-d2.py" artifact \
        "$tree" "$diagnostics/artifact-check.json"
    # Only publish firmware after every check has passed. Diagnostics survive failure.
    [[ ! -e "$artifact_root/firmware" ]] || {
        printf 'Refusing to mix new firmware with existing artifacts. Use a new ARTIFACT_ROOT.\n' >&2
        return 1
    }
    mkdir -p "$artifact_root/firmware"
    local target_dir="$tree/bin/targets/ramips/mt7621"
    cp "$target_dir/"*d-team_newifi-d2-squashfs-sysupgrade.bin "$artifact_root/firmware/"
    cp "$target_dir/"*.manifest "$artifact_root/firmware/packages.manifest"
    cp "$target_dir/profiles.json" "$artifact_root/firmware/"
    cp "$diagnostics/final.config" "$diagnostics/diff.config" \
        "$diagnostics/sources.json" "$diagnostics/config-check.json" \
        "$diagnostics/artifact-check.json" "$artifact_root/firmware/"
    cp "$profile_dir/README.md" "$profile_dir/VALIDATION.md" "$artifact_root/firmware/"
    (cd "$artifact_root/firmware" && sha256sum ./*.bin > SHA256SUMS)
    cat "$artifact_root/firmware/SHA256SUMS"
}

case "$mode" in
    prepare)
        clone_exact "$OPENWRT_URL" "$OPENWRT_COMMIT" "$tree"
        # Partial sparse checkout fetches only the plugin's blobs, never a core package.
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
            printf 'The Git server must support partial clone; refusing an unrestricted feed.\n' >&2
            exit 1
        fi
        git -C "$openclash_feed" checkout --detach FETCH_HEAD
        [[ $(git -C "$openclash_feed" rev-parse HEAD) == "$OPENCLASH_COMMIT" ]]
        patch --batch --fuzz=0 -p1 -d "$openclash_feed" \
            < "$profile_dir/patches/openclash-host-build.patch"
        cat > "$tree/feeds.conf" <<EOF
src-git packages $PACKAGES_URL^$PACKAGES_COMMIT
src-git luci $LUCI_URL^$LUCI_COMMIT
src-link openclash $openclash_feed
EOF
        cp "$profile_dir/config" "$tree/.config"
        cp -a "$profile_dir/files" "$tree/files"
        chmod 0755 "$tree/files/etc/uci-defaults/zz-newifi-d2-openclash"
        (cd "$tree" && ./scripts/feeds update -a)
        (cd "$tree" && ./scripts/feeds install \
            luci-light luci-compat luci-lib-ipkg luci-app-openclash)
        [[ $(git -C "$tree/feeds/packages" rev-parse HEAD) == "$PACKAGES_COMMIT" ]]
        [[ $(git -C "$tree/feeds/luci" rev-parse HEAD) == "$LUCI_COMMIT" ]]
        # feeds refreshes Kconfig while installing packages; reapply the full intent.
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
            # Retry serially with diagnostics; errors still fail the job.
            run_make -j1 V=s 2>&1 | tee "$diagnostics/build-serial.log"
        fi
        collect
        ;;
    collect)
        collect
        ;;
    *) printf 'Unknown mode: %s\n' "$mode" >&2; exit 2 ;;
esac
