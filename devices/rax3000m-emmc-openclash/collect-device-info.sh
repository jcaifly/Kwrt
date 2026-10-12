#!/bin/sh
# Run manually on the router. Only read system/partition/upgrade information.
# No UCI/network/Wi-Fi/OpenClash configuration, complete env dump or raw backup.
set -u

section() { printf '\n### %s\n' "$1"; }
read_file() {
    [ -r "$1" ] || return 0
    printf '\nFILE %s\n' "$1"
    cat "$1"
    printf '\n'
}
read_dt() {
    [ -r "$1" ] || return 0
    printf '\nDT %s\n' "$1"
    tr '\000' '\n' < "$1"
}

section 'Release, board and memory'
uname -r
read_file /etc/openwrt_release
read_file /etc/os-release
read_file /tmp/sysinfo/board_name
read_dt /sys/firmware/devicetree/base/model
read_dt /sys/firmware/devicetree/base/compatible
grep '^MemTotal:' /proc/meminfo

section 'Boot parameters (review for private values before sharing)'
read_file /proc/cmdline
read_dt /sys/firmware/devicetree/base/chosen/bootargs
read_dt /sys/firmware/devicetree/base/chosen/bootargs-override
if [ -r /sys/firmware/devicetree/base/chosen/rootdisk ]; then
    printf 'chosen/rootdisk phandle: '
    od -An -tx1 /sys/firmware/devicetree/base/chosen/rootdisk
fi
read_file /etc/fw_env.config
if command -v fw_printenv >/dev/null 2>&1; then
    for variable in ver bootcmd bootargs bootconf bootmenu_0; do
        printf '\nENV %s (single named variable only)\n' "$variable"
        fw_printenv -n "$variable" 2>/dev/null || :
    done
fi

section 'eMMC partition positions in 512-byte sectors; never resize'
for device in /sys/class/block/mmcblk*; do
    [ -d "$device" ] || continue
    printf '\nBLOCK %s\n' "${device##*/}"
    for field in start size ro partition; do
        [ ! -r "$device/$field" ] || {
            printf '%s=' "$field"
            cat "$device/$field"
        }
    done
    grep -E '^(DEVNAME|PARTN|PARTNAME|PARTUUID)=' "$device/uevent" || :
    if [ -r "$device/start" ] && [ -r "$device/size" ]; then
        start=$(cat "$device/start")
        size=$(cat "$device/size")
        printf 'end_sector=%s size_bytes=%s\n' "$((start + size - 1))" "$((size * 512))"
    fi
    read_dt "$device/of_node/partname"
    if [ -r "$device/of_node/phandle" ]; then
        printf 'of_node/phandle: '
        od -An -tx1 "$device/of_node/phandle"
    fi
done
if [ -b /dev/mmcblk0 ] && command -v fdisk >/dev/null 2>&1; then
    fdisk -l /dev/mmcblk0 || :
fi
section 'Current mount destinations'
read_file /proc/mounts
read_file /proc/partitions
df -h / /rom /overlay 2>/dev/null || :

section 'Current upgrade logic (printed as text; never sourced or run)'
for script in /sbin/sysupgrade /lib/upgrade/platform.sh /lib/upgrade/fit.sh \
    /lib/upgrade/emmc.sh /lib/upgrade/mmc.sh /lib/upgrade/fwtool.sh \
    /usr/libexec/validate_firmware_image; do
    [ -r "$script" ] || continue
    printf '\nSCRIPT %s\n' "$script"
    # Sourced .sh files often have no shebang. Never execute either kind.
    case "$script" in
        /lib/upgrade/*.sh|/sbin/sysupgrade) cat "$script" ;;
        *)
            if [ "$(dd if="$script" bs=2 count=1 2>/dev/null)" = '#!' ]; then
                cat "$script"
            else
                printf 'Binary validator; source/version evidence required if behavior is unknown.\n'
            fi
            ;;
    esac
done
printf '\nCollection finished. No image was checked, installed, backed up or flashed.\n'
printf 'Review and redact any private boot URLs/identifiers before sending this report.\n'
