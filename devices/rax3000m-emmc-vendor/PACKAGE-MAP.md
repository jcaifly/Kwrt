# 商家 375 个包与 25.12 构建逐项对照

商家参考 SHA256：`1a6e955f0923489f474fb9a8ecac4cb64527a8c42abf4a47082539f49fd45d43`。
全部 375 项都有明确对应，不假称版本字节完全相同；这是源码元数据和最终 defconfig 检查结果，实际安装包版本以编译后的 manifest 为准。
`<LINUX_VERSION>` / `<LIBGCC_VERSION>` 是构建元数据占位符，不能当作已编译结果；kernel 自动生成真实 ABI。
原 opkg 用原生 APK 替代，my-default-settings 为本构建的安全默认设置版本；luci-lib-fs 使用原商家纯文本 Apache-2.0 Lua 源码并调用新系统的 nixio，未复用商家 ELF 或内核模块。
Mihomo v1.19.32 为新增例外；quickstart 和 chinadns-ng 的上游配方使用发布者 ARM64 预构建文件，均补齐固定 SHA256，不能宣称它们在本次从源码重新编译。
其余包使用固定 25.12 源码/feeds 或固定 vendor feed 重建；源码包版本、ABI 后缀和额外必要依赖可能与商家不同。

新增 OpenClash 0.48.002-r9 与 openclash-mihomo-core 1.19.32-r1；小闪存模式关闭。

| 商家包 | 商家版本 | 新构建选择符号 | 25.12 源码包版本 | 对应方式 |
| --- | --- | --- | --- | --- |
| autocore | 2 | autocore | 2 | same package name |
| automount | 1 | automount | 1 | same package name |
| base-files | 1712~07.15.2026 | base-files | 0~f5dae5ece4 | same package name |
| bash | 5.3-r4 | bash | 5.3-r4 | same package name |
| bc | 1.08.2-r1 | bc | 1.08.2-r1 | same package name |
| blkid | 2.41.5-r1 | blkid | 2.41.5-r1 | same package name |
| block-mount | 2026.05.23~16718b6e-r1 | block-mount | 2026.05.23~16718b6e3c0fc7db7be6ae5848db0eae88ac8a8b-r1 | same package name |
| btrfs-progs | 6.11-r3 | btrfs-progs | 6.11-r3 | same package name |
| busybox | 1.37.0-r6 | busybox | 1.37.0-r6 | same package name |
| bzip2 | 1.0.8-r1 | bzip2 | 1.0.8-r1 | same package name |
| ca-bundle | 20260601-r1 | ca-bundle | 20260601-r1 | same package name |
| cgi-io | 2026.06.28~7314451c-r1 | cgi-io | 2026.06.28~7314451cb99692c0862a70c3307ee08bd2fbd9c0-r1 | same package name |
| chinadns-ng | 2025.08.09-r1 | chinadns-ng | 2025.08.09-r1 | same package name |
| coremark | 2025.05.01~1f483d5b-r2 | coremark | 2025.05.01~1f483d5b8316753a742cbf5590caf5bd0a4e4777-r1 | same package name |
| coreutils | 9.9-r2 | coreutils | 9.9-r2 | same package name |
| coreutils-base64 | 9.9-r2 | coreutils-base64 | 9.9-r2 | same package name |
| coreutils-nohup | 9.9-r2 | coreutils-nohup | 9.9-r2 | same package name |
| coreutils-stat | 9.9-r2 | coreutils-stat | 9.9-r2 | same package name |
| coreutils-stty | 9.9-r2 | coreutils-stty | 9.9-r2 | same package name |
| coreutils-timeout | 9.9-r2 | coreutils-timeout | 9.9-r2 | same package name |
| curl | 8.19.0-r2 | curl | 8.19.0-r2 | same package name |
| dns2socks | 2.1-r1 | dns2socks | 2.1-r1 | same package name |
| dnsmasq-full | 2.93-r1 | dnsmasq-full | 2.93-r1 | same package name |
| dosfstools | 4.2-r4 | dosfstools | 4.2-r4 | same package name |
| dropbear | 2025.89-r3 | dropbear | 2025.89-r3 | same package name |
| ds-lite | 9 | ds-lite | 9 | same package name |
| e2fsprogs | 1.47.3-r1 | e2fsprogs | 1.47.3-r1 | same package name |
| eip197-mini-firmware | 20260221-r1 | eip197-mini-firmware | 20260221-r1 | same package name |
| exfat-fsck | 1.2.9-r1 | exfat-fsck | 1.2.9-r1 | same package name |
| exfat-mkfs | 1.2.9-r1 | exfat-mkfs | 1.2.9-r1 | same package name |
| f2fs-tools | 1.16.0-r4 | f2fs-tools | 1.16.0-r4 | same package name |
| f2fsck | 1.16.0-r4 | f2fsck | 1.16.0-r4 | same package name |
| fdisk | 2.41.5-r1 | fdisk | 2.41.5-r1 | same package name |
| firewall4 | 2025.03.17~b6e51575-r2 | firewall4 | 2025.03.17~b6e5157527d361f99ad52eaa6da273cb0f2dfd59-r2 | same package name |
| fit-check-sign | 2025.10-r2 | fit-check-sign | 2025.10-r2 | same package name |
| fitblk | 2 | fitblk | 2 | same package name |
| fstools | 2026.05.23~16718b6e-r1 | fstools | 2026.05.23~16718b6e3c0fc7db7be6ae5848db0eae88ac8a8b-r1 | same package name |
| fwtool | 2025.10.03~04cd252e-r1 | fwtool | 2025.10.03~04cd252e4e9394ffacd51f56f1f124abc534f715-r1 | same package name |
| geoview | 0.2.6-r5 | geoview | 0.2.6-r7 | same package name |
| getrandom | 2025.10.30~6f78fa49-r1 | getrandom | 2025.10.30~6f78fa496bf36c55864a41e353df7d13f04b1077-r1 | same package name |
| haproxy | 3.2.19-r1 | haproxy | 3.2.15-r1 | same package name |
| hostapd-common | 2025.08.26~ca266cc2-r2 | hostapd-common | 2025.08.26~ca266cc24d8705eb1a2a0857ad326e48b1408b20-r1 | same package name |
| htop | 3.5.1-r1 | htop | 3.5.1-r1 | same package name |
| ip-full | 6.18.0-r2 | ip-full | 6.18.0-r2 | same package name |
| ip6tables-zz-legacy | 1.8.10-r3 | ip6tables-zz-legacy | 1.8.10-r3 | same package name |
| ipt2socks | 1.1.4-r1 | ipt2socks | 1.1.4-r1 | same package name |
| iptables-nft | 1.8.10-r3 | iptables-nft | 1.8.10-r3 | same package name |
| iw | 6.17-r1 | iw | 6.17-r1 | same package name |
| jansson4 | 2.14.1-r1 | jansson | 2.14.1-r1 | ABI-name mapping |
| jshn | 2026.06.19~7dd12784-r1 | jshn | 2026.06.19~7dd127841e82eb1cfb61185da37dde7b9bd9ba6d-r1 | same package name |
| jsonfilter | 2026.03.16~b9034210-r1 | jsonfilter | 2026.03.16~b9034210bd331749673416c6bf389cccd4e23610-r1 | same package name |
| kernel | 6.12.94~1-r1 | 自动 Linux 构建 | 自动 Linux 构建 | automatic Linux build; true ABI, never vendor ~1 |
| kmod-cfg80211 | 6.12.94.6.18.26-r1 | kmod-cfg80211 | <LINUX_VERSION>.6.18.26-r1 | same package name |
| kmod-crypto-acompress | 6.12.94-r1 | kmod-crypto-acompress | <LINUX_VERSION>-r | same package name |
| kmod-crypto-aead | 6.12.94-r1 | kmod-crypto-aead | <LINUX_VERSION>-r | same package name |
| kmod-crypto-arc4 | 6.12.94-r1 | kmod-crypto-arc4 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-authenc | 6.12.94-r1 | kmod-crypto-authenc | <LINUX_VERSION>-r | same package name |
| kmod-crypto-blake2b | 6.12.94-r1 | kmod-crypto-blake2b | <LINUX_VERSION>-r | same package name |
| kmod-crypto-ccm | 6.12.94-r1 | kmod-crypto-ccm | <LINUX_VERSION>-r | same package name |
| kmod-crypto-cmac | 6.12.94-r1 | kmod-crypto-cmac | <LINUX_VERSION>-r | same package name |
| kmod-crypto-crc32 | 6.12.94-r1 | kmod-crypto-crc32 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-crc32c | 6.12.94-r1 | kmod-crypto-crc32c | <LINUX_VERSION>-r | same package name |
| kmod-crypto-ctr | 6.12.94-r1 | kmod-crypto-ctr | <LINUX_VERSION>-r | same package name |
| kmod-crypto-des | 6.12.94-r1 | kmod-crypto-des | <LINUX_VERSION>-r | same package name |
| kmod-crypto-ecb | 6.12.94-r1 | kmod-crypto-ecb | <LINUX_VERSION>-r | same package name |
| kmod-crypto-gcm | 6.12.94-r1 | kmod-crypto-gcm | <LINUX_VERSION>-r | same package name |
| kmod-crypto-geniv | 6.12.94-r1 | kmod-crypto-geniv | <LINUX_VERSION>-r | same package name |
| kmod-crypto-gf128 | 6.12.94-r1 | kmod-crypto-gf128 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-ghash | 6.12.94-r1 | kmod-crypto-ghash | <LINUX_VERSION>-r | same package name |
| kmod-crypto-hash | 6.12.94-r1 | kmod-crypto-hash | <LINUX_VERSION>-r | same package name |
| kmod-crypto-hmac | 6.12.94-r1 | kmod-crypto-hmac | <LINUX_VERSION>-r | same package name |
| kmod-crypto-hw-safexcel | 6.12.94-r1 | kmod-crypto-hw-safexcel | <LINUX_VERSION>-r | same package name |
| kmod-crypto-manager | 6.12.94-r1 | kmod-crypto-manager | <LINUX_VERSION>-r | same package name |
| kmod-crypto-md5 | 6.12.94-r1 | kmod-crypto-md5 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-null | 6.12.94-r1 | kmod-crypto-null | <LINUX_VERSION>-r | same package name |
| kmod-crypto-rng | 6.12.94-r1 | kmod-crypto-rng | <LINUX_VERSION>-r | same package name |
| kmod-crypto-seqiv | 6.12.94-r1 | kmod-crypto-seqiv | <LINUX_VERSION>-r | same package name |
| kmod-crypto-sha1 | 6.12.94-r1 | kmod-crypto-sha1 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-sha256 | 6.12.94-r1 | kmod-crypto-sha256 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-sha3 | 6.12.94-r1 | kmod-crypto-sha3 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-sha512 | 6.12.94-r1 | kmod-crypto-sha512 | <LINUX_VERSION>-r | same package name |
| kmod-crypto-user | 6.12.94-r1 | kmod-crypto-user | <LINUX_VERSION>-r | same package name |
| kmod-crypto-xxhash | 6.12.94-r1 | kmod-crypto-xxhash | <LINUX_VERSION>-r | same package name |
| kmod-fs-btrfs | 6.12.94-r1 | kmod-fs-btrfs | <LINUX_VERSION>-r | same package name |
| kmod-fs-exfat | 6.12.94-r1 | kmod-fs-exfat | <LINUX_VERSION>-r | same package name |
| kmod-fs-ext4 | 6.12.94-r1 | kmod-fs-ext4 | <LINUX_VERSION>-r | same package name |
| kmod-fs-f2fs | 6.12.94-r1 | kmod-fs-f2fs | <LINUX_VERSION>-r | same package name |
| kmod-fs-msdos | 6.12.94-r1 | kmod-fs-msdos | <LINUX_VERSION>-r | same package name |
| kmod-fs-ntfs3 | 6.12.94-r1 | kmod-fs-ntfs3 | <LINUX_VERSION>-r | same package name |
| kmod-fs-vfat | 6.12.94-r1 | kmod-fs-vfat | <LINUX_VERSION>-r | same package name |
| kmod-gpio-button-hotplug | 6.12.94-r5 | kmod-gpio-button-hotplug | <LINUX_VERSION>-r5 | same package name |
| kmod-hwmon-core | 6.12.94-r1 | kmod-hwmon-core | <LINUX_VERSION>-r | same package name |
| kmod-hwmon-pwmfan | 6.12.94-r1 | kmod-hwmon-pwmfan | <LINUX_VERSION>-r | same package name |
| kmod-i2c-core | 6.12.94-r1 | kmod-i2c-core | <LINUX_VERSION>-r | same package name |
| kmod-inet-diag | 6.12.94-r1 | kmod-inet-diag | <LINUX_VERSION>-r | same package name |
| kmod-ip6-tunnel | 6.12.94-r1 | kmod-ip6-tunnel | <LINUX_VERSION>-r | same package name |
| kmod-ip6tables | 6.12.94-r1 | kmod-ip6tables | <LINUX_VERSION>-r | same package name |
| kmod-ipt-core | 6.12.94-r1 | kmod-ipt-core | <LINUX_VERSION>-r | same package name |
| kmod-ipt-ipset | 6.12.94-r1 | kmod-ipt-ipset | <LINUX_VERSION>-r | same package name |
| kmod-iptunnel6 | 6.12.94-r1 | kmod-iptunnel6 | <LINUX_VERSION>-r | same package name |
| kmod-leds-gpio | 6.12.94-r1 | kmod-leds-gpio | <LINUX_VERSION>-r | same package name |
| kmod-lib-crc-ccitt | 6.12.94-r1 | kmod-lib-crc-ccitt | <LINUX_VERSION>-r | same package name |
| kmod-lib-crc16 | 6.12.94-r1 | kmod-lib-crc16 | <LINUX_VERSION>-r | same package name |
| kmod-lib-crc32c | 6.12.94-r1 | kmod-lib-crc32c | <LINUX_VERSION>-r | same package name |
| kmod-lib-lzo | 6.12.94-r1 | kmod-lib-lzo | <LINUX_VERSION>-r | same package name |
| kmod-lib-raid6 | 6.12.94-r1 | kmod-lib-raid6 | <LINUX_VERSION>-r | same package name |
| kmod-lib-xor | 6.12.94-r1 | kmod-lib-xor | <LINUX_VERSION>-r | same package name |
| kmod-lib-xxhash | 6.12.94-r1 | kmod-lib-xxhash | <LINUX_VERSION>-r | same package name |
| kmod-lib-zlib-deflate | 6.12.94-r1 | kmod-lib-zlib-deflate | <LINUX_VERSION>-r | same package name |
| kmod-lib-zlib-inflate | 6.12.94-r1 | kmod-lib-zlib-inflate | <LINUX_VERSION>-r | same package name |
| kmod-lib-zstd | 6.12.94-r1 | kmod-lib-zstd | <LINUX_VERSION>-r | same package name |
| kmod-loop | 6.12.94-r1 | kmod-loop | <LINUX_VERSION>-r | same package name |
| kmod-mac80211 | 6.12.94.6.18.26-r1 | kmod-mac80211 | <LINUX_VERSION>.6.18.26-r1 | same package name |
| kmod-macvlan | 6.12.94-r1 | kmod-macvlan | <LINUX_VERSION>-r | same package name |
| kmod-md-mod | 6.12.94-r1 | kmod-md-mod | <LINUX_VERSION>-r | same package name |
| kmod-md-raid0 | 6.12.94-r1 | kmod-md-raid0 | <LINUX_VERSION>-r | same package name |
| kmod-md-raid1 | 6.12.94-r1 | kmod-md-raid1 | <LINUX_VERSION>-r | same package name |
| kmod-md-raid10 | 6.12.94-r1 | kmod-md-raid10 | <LINUX_VERSION>-r | same package name |
| kmod-mmc | 6.12.94-r1 | kmod-mmc | <LINUX_VERSION>-r | same package name |
| kmod-mppe | 6.12.94-r1 | kmod-mppe | <LINUX_VERSION>-r | same package name |
| kmod-mt76-connac | 6.12.94.2026.03.19~39c960c3-r2 | kmod-mt76-connac | <LINUX_VERSION>.2026.03.19~39c960c3ada558b4c2e7915772483d3731573d09-r2 | same package name |
| kmod-mt76-core | 6.12.94.2026.03.19~39c960c3-r2 | kmod-mt76-core | <LINUX_VERSION>.2026.03.19~39c960c3ada558b4c2e7915772483d3731573d09-r2 | same package name |
| kmod-mt7915e | 6.12.94.2026.03.19~39c960c3-r2 | kmod-mt7915e | <LINUX_VERSION>.2026.03.19~39c960c3ada558b4c2e7915772483d3731573d09-r2 | same package name |
| kmod-mt7981-firmware | 6.12.94.2026.03.19~39c960c3-r2 | kmod-mt7981-firmware | <LINUX_VERSION>.2026.03.19~39c960c3ada558b4c2e7915772483d3731573d09-r2 | same package name |
| kmod-netlink-diag | 6.12.94-r1 | kmod-netlink-diag | <LINUX_VERSION>-r | same package name |
| kmod-nf-conntrack | 6.12.94-r1 | kmod-nf-conntrack | <LINUX_VERSION>-r | same package name |
| kmod-nf-conntrack-netlink | 6.12.94-r1 | kmod-nf-conntrack-netlink | <LINUX_VERSION>-r | same package name |
| kmod-nf-conntrack6 | 6.12.94-r1 | kmod-nf-conntrack6 | <LINUX_VERSION>-r | same package name |
| kmod-nf-flow | 6.12.94-r1 | kmod-nf-flow | <LINUX_VERSION>-r | same package name |
| kmod-nf-ipt | 6.12.94-r1 | kmod-nf-ipt | <LINUX_VERSION>-r | same package name |
| kmod-nf-ipt6 | 6.12.94-r1 | kmod-nf-ipt6 | <LINUX_VERSION>-r | same package name |
| kmod-nf-log | 6.12.94-r1 | kmod-nf-log | <LINUX_VERSION>-r | same package name |
| kmod-nf-log6 | 6.12.94-r1 | kmod-nf-log6 | <LINUX_VERSION>-r | same package name |
| kmod-nf-nat | 6.12.94-r1 | kmod-nf-nat | <LINUX_VERSION>-r | same package name |
| kmod-nf-reject | 6.12.94-r1 | kmod-nf-reject | <LINUX_VERSION>-r | same package name |
| kmod-nf-reject6 | 6.12.94-r1 | kmod-nf-reject6 | <LINUX_VERSION>-r | same package name |
| kmod-nf-socket | 6.12.94-r1 | kmod-nf-socket | <LINUX_VERSION>-r | same package name |
| kmod-nf-tproxy | 6.12.94-r1 | kmod-nf-tproxy | <LINUX_VERSION>-r | same package name |
| kmod-nfnetlink | 6.12.94-r1 | kmod-nfnetlink | <LINUX_VERSION>-r | same package name |
| kmod-nft-compat | 6.12.94-r1 | kmod-nft-compat | <LINUX_VERSION>-r | same package name |
| kmod-nft-core | 6.12.94-r1 | kmod-nft-core | <LINUX_VERSION>-r | same package name |
| kmod-nft-fib | 6.12.94-r1 | kmod-nft-fib | <LINUX_VERSION>-r | same package name |
| kmod-nft-fullcone | 6.12.94.2023.05.17~07d93b62-r1 | kmod-nft-fullcone | <LINUX_VERSION>.2023.05.17~07d93b62-r1 | same package name |
| kmod-nft-nat | 6.12.94-r1 | kmod-nft-nat | <LINUX_VERSION>-r | same package name |
| kmod-nft-offload | 6.12.94-r1 | kmod-nft-offload | <LINUX_VERSION>-r | same package name |
| kmod-nft-socket | 6.12.94-r1 | kmod-nft-socket | <LINUX_VERSION>-r | same package name |
| kmod-nft-tproxy | 6.12.94-r1 | kmod-nft-tproxy | <LINUX_VERSION>-r | same package name |
| kmod-nls-base | 6.12.94-r1 | kmod-nls-base | <LINUX_VERSION>-r | same package name |
| kmod-nls-cp437 | 6.12.94-r1 | kmod-nls-cp437 | <LINUX_VERSION>-r | same package name |
| kmod-nls-cp932 | 6.12.94-r1 | kmod-nls-cp932 | <LINUX_VERSION>-r | same package name |
| kmod-nls-cp936 | 6.12.94-r1 | kmod-nls-cp936 | <LINUX_VERSION>-r | same package name |
| kmod-nls-cp950 | 6.12.94-r1 | kmod-nls-cp950 | <LINUX_VERSION>-r | same package name |
| kmod-nls-iso8859-1 | 6.12.94-r1 | kmod-nls-iso8859-1 | <LINUX_VERSION>-r | same package name |
| kmod-nls-utf8 | 6.12.94-r1 | kmod-nls-utf8 | <LINUX_VERSION>-r | same package name |
| kmod-ppp | 6.12.94-r1 | kmod-ppp | <LINUX_VERSION>-r | same package name |
| kmod-pppoe | 6.12.94-r1 | kmod-pppoe | <LINUX_VERSION>-r | same package name |
| kmod-pppox | 6.12.94-r1 | kmod-pppox | <LINUX_VERSION>-r | same package name |
| kmod-scsi-core | 6.12.94-r1 | kmod-scsi-core | <LINUX_VERSION>-r | same package name |
| kmod-slhc | 6.12.94-r1 | kmod-slhc | <LINUX_VERSION>-r | same package name |
| kmod-tcp-bbr | 6.12.94-r1 | kmod-tcp-bbr | <LINUX_VERSION>-r | same package name |
| kmod-thermal | 6.12.94-r1 | kmod-thermal | <LINUX_VERSION>-r | same package name |
| kmod-tun | 6.12.94-r1 | kmod-tun | <LINUX_VERSION>-r | same package name |
| kmod-usb-common | 6.12.94-r1 | kmod-usb-common | <LINUX_VERSION>-r | same package name |
| kmod-usb-core | 6.12.94-r1 | kmod-usb-core | <LINUX_VERSION>-r | same package name |
| kmod-usb-storage | 6.12.94-r1 | kmod-usb-storage | <LINUX_VERSION>-r | same package name |
| kmod-usb-storage-extras | 6.12.94-r1 | kmod-usb-storage-extras | <LINUX_VERSION>-r | same package name |
| kmod-usb-storage-uas | 6.12.94-r1 | kmod-usb-storage-uas | <LINUX_VERSION>-r | same package name |
| kmod-usb-xhci-hcd | 6.12.94-r1 | kmod-usb-xhci-hcd | <LINUX_VERSION>-r | same package name |
| kmod-usb-xhci-mtk | 6.12.94-r1 | kmod-usb-xhci-mtk | <LINUX_VERSION>-r | same package name |
| kmod-usb3 | 6.12.94-r1 | kmod-usb3 | <LINUX_VERSION>-r | same package name |
| kmod-zram | 6.12.94-r1 | kmod-zram | <LINUX_VERSION>-r | same package name |
| libacl | 2.3.2-r2 | libacl | 2.3.2-r2 | same package name |
| libatomic1 | 14.3.0-r5 | libatomic | <LIBGCC_VERSION>-r5 | ABI-name mapping |
| libattr | 2.5.2-r3 | libattr | 2.5.2-r3 | same package name |
| libblkid1 | 2.41.5-r1 | libblkid | 2.41.5-r1 | ABI-name mapping |
| libblobmsg-json20260213 | 2026.06.19~7dd12784-r1 | libblobmsg-json | 2026.06.19~7dd127841e82eb1cfb61185da37dde7b9bd9ba6d-r1 | ABI-name mapping |
| libbpf1 | 1.6.2-r1 | libbpf | 1.6.2-r1 | ABI-name mapping |
| libbz2-1.0 | 1.0.8-r1 | libbz2 | 1.0.8-r1 | ABI-name mapping |
| libc | 1.2.5-r5 | libc | <LIBC_VERSION>-r5 | same package name |
| libcap | 2.69-r1 | libcap | 2.69-r1 | same package name |
| libcap-ng | 0.8.4-r2 | libcap-ng | 0.8.4-r2 | same package name |
| libcomerr0 | 1.47.3-r1 | libcomerr | 1.47.3-r1 | ABI-name mapping |
| libcurl4 | 8.19.0-r2 | libcurl | 8.19.0-r2 | ABI-name mapping |
| libe2p2 | 1.47.3-r1 | libe2p | 1.47.3-r1 | ABI-name mapping |
| libelf1 | 0.192-r1 | libelf | 0.192-r1 | ABI-name mapping |
| libev | 4.33-r3 | libev | 4.33-r3 | same package name |
| libext2fs2 | 1.47.3-r1 | libext2fs | 1.47.3-r1 | ABI-name mapping |
| libf2fs6 | 1.16.0-r4 | libf2fs | 1.16.0-r4 | ABI-name mapping |
| libfdisk1 | 2.41.5-r1 | libfdisk | 2.41.5-r1 | ABI-name mapping |
| libgcc1 | 14.3.0-r5 | libgcc | <LIBGCC_VERSION>-r5 | ABI-name mapping |
| libgmp10 | 6.3.0-r2 | libgmp | 6.3.0-r2 | ABI-name mapping |
| libip4tc2 | 1.8.10-r3 | libip4tc | 1.8.10-r3 | ABI-name mapping |
| libip6tc2 | 1.8.10-r3 | libip6tc | 1.8.10-r3 | ABI-name mapping |
| libiptext-nft0 | 1.8.10-r3 | libiptext-nft | 1.8.10-r3 | ABI-name mapping |
| libiptext0 | 1.8.10-r3 | libiptext | 1.8.10-r3 | ABI-name mapping |
| libiptext6-0 | 1.8.10-r3 | libiptext6 | 1.8.10-r3 | ABI-name mapping |
| libiwinfo-data | 2026.01.14~f5dd57a8-r1 | libiwinfo-data | 2026.01.14~f5dd57a84cc31a403a1383dd14944fa2e2b5824a-r1 | same package name |
| libiwinfo20230701 | 2026.01.14~f5dd57a8-r1 | libiwinfo | 2026.01.14~f5dd57a84cc31a403a1383dd14944fa2e2b5824a-r1 | ABI-name mapping |
| libjson-c5 | 0.18-r1 | libjson-c | 0.18-r1 | ABI-name mapping |
| libjson-script20260213 | 2026.06.19~7dd12784-r1 | libjson-script | 2026.06.19~7dd127841e82eb1cfb61185da37dde7b9bd9ba6d-r1 | ABI-name mapping |
| libltdl7 | 2.5.4-r1 | libltdl | 2.5.4-r1 | ABI-name mapping |
| liblua5.1.5 | 5.1.5-r11 | liblua | 5.1.5-r11 | ABI-name mapping |
| liblua5.4-5.4 | 5.4.7-r1 | liblua5.4 | 5.4.7-r1 | ABI-name mapping |
| liblucihttp-lua | 2023.03.15~9b5b683f-r1 | liblucihttp-lua | 2023.03.15~9b5b683fbb2bb0010aa031d620d0ab8105516757-r1 | same package name |
| liblucihttp-ucode | 2023.03.15~9b5b683f-r1 | liblucihttp-ucode | 2023.03.15~9b5b683fbb2bb0010aa031d620d0ab8105516757-r1 | same package name |
| liblucihttp0 | 2023.03.15~9b5b683f-r1 | liblucihttp | 2023.03.15~9b5b683fbb2bb0010aa031d620d0ab8105516757-r1 | ABI-name mapping |
| liblzma | 5.8.1-r1 | liblzma | 5.8.1-r1 | same package name |
| liblzo2 | 2.10-r5 | liblzo | 2.10-r5 | ABI-name mapping |
| libmbedtls21 | 3.6.6-r2 | libmbedtls | 3.6.6-r2 | ABI-name mapping |
| libmnl0 | 1.0.5-r1 | libmnl | 1.0.5-r1 | ABI-name mapping |
| libmount1 | 2.41.5-r1 | libmount | 2.41.5-r1 | ABI-name mapping |
| libncurses6 | 6.4-r3 | libncurses | 6.4-r3 | ABI-name mapping |
| libnetfilter-conntrack3 | 1.1.0-r1 | libnetfilter-conntrack | 1.1.0-r1 | ABI-name mapping |
| libnettle8 | 3.10.2-r1 | libnettle | 3.10.2-r1 | ABI-name mapping |
| libnfnetlink0 | 1.0.2-r1 | libnfnetlink | 1.0.2-r1 | ABI-name mapping |
| libnftnl11 | 1.3.1-r1 | libnftnl | 1.3.1-r1 | ABI-name mapping |
| libnghttp2-14 | 1.66.0-r1 | libnghttp2 | 1.66.0-r1 | ABI-name mapping |
| libnl-tiny1 | 2025.12.02~40493a65-r1 | libnl-tiny | 2025.12.02~40493a655d8caa2ccf5206dde1e733abe2920432-r1 | ABI-name mapping |
| libopenssl3 | 3.5.7-r1 | libopenssl | 3.5.7-r1 | ABI-name mapping |
| libparted | 3.6-r2 | libparted | 3.6-r2 | same package name |
| libpcre2 | 10.47-r1 | libpcre2 | 10.47-r1 | same package name |
| libpthread | 1.2.5-r5 | libpthread | <LIBC_VERSION>-r5 | same package name |
| libreadline8 | 8.3-r1 | libreadline | 8.3-r1 | ABI-name mapping |
| librt | 1.2.5-r5 | librt | <LIBC_VERSION>-r5 | same package name |
| libsmartcols1 | 2.41.5-r1 | libsmartcols | 2.41.5-r1 | ABI-name mapping |
| libsodium | 1.0.20-r1 | libsodium | 1.0.20-r1 | same package name |
| libss2 | 1.47.3-r1 | libss | 1.47.3-r1 | ABI-name mapping |
| libstdcpp6 | 14.3.0-r5 | libstdcpp | <LIBGCC_VERSION>-r5 | ABI-name mapping |
| libubox20260213 | 2026.06.19~7dd12784-r1 | libubox | 2026.06.19~7dd127841e82eb1cfb61185da37dde7b9bd9ba6d-r1 | ABI-name mapping |
| libubus-lua | 2026.06.28~24864e78-r2 | libubus-lua | 2026.06.28~24864e7840b3a02a9ef76284a373f6b2f00b8a9b-r2 | same package name |
| libubus20251202 | 2026.06.28~24864e78-r2 | libubus | 2026.06.28~24864e7840b3a02a9ef76284a373f6b2f00b8a9b-r2 | ABI-name mapping |
| libuci-lua | 2025.12.02~66127cd7-r1 | libuci-lua | 2025.12.02~66127cd76c5d0bd46d5a90302cc6110f53a4e2f8-r1 | same package name |
| libuci20250120 | 2025.12.02~66127cd7-r1 | libuci | 2025.12.02~66127cd76c5d0bd46d5a90302cc6110f53a4e2f8-r1 | ABI-name mapping |
| libuclient20201210 | 2026.06.07~daad21fa-r1 | libuclient | 2026.06.07~daad21fa2c17cae54d37149bf27bb3dd78e50a3f-r1 | ABI-name mapping |
| libucode20230711 | 2026.01.16~85922056-r1 | libucode | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | ABI-name mapping |
| libudebug | 2026.01.16~875e1a7a | libudebug | 2026.01.16~875e1a7af6ca9d86524d18169c3a79f4a1920053 | same package name |
| libudns | 0.4-r1 | libudns | 0.4-r1 | same package name |
| libustream-mbedtls20201210 | 2026.03.01~99f1c0db-r1 | libustream-mbedtls | 2026.03.01~99f1c0db5a729f615bc5114b3b52fd8ac8083f34-r1 | ABI-name mapping |
| libuuid1 | 2.41.5-r1 | libuuid | 2.41.5-r1 | ABI-name mapping |
| libuv1 | 1.48.0-r1 | libuv | 1.48.0-r1 | ABI-name mapping |
| libwebsockets-full | 4.4.1-r1 | libwebsockets-full | 4.4.1-r1 | same package name |
| libxml2-16 | 2.15.1-r1 | libxml2 | 2.15.1-r1 | ABI-name mapping |
| libxtables12 | 1.8.10-r3 | libxtables | 1.8.10-r3 | ABI-name mapping |
| libyaml | 0.2.5-r2 | libyaml | 0.2.5-r2 | same package name |
| libzstd | 1.5.7-r1 | libzstd | 1.5.7-r1 | same package name |
| logd | 2025.10.30~6f78fa49-r1 | logd | 2025.10.30~6f78fa496bf36c55864a41e353df7d13f04b1077-r1 | same package name |
| losetup | 2.41.5-r1 | losetup | 2.41.5-r1 | same package name |
| lsblk | 2.41.5-r1 | lsblk | 2.41.5-r1 | same package name |
| lua | 5.1.5-r11 | lua | 5.1.5-r11 | same package name |
| luci-app-advancedplus | 1.8.9-r2 | luci-app-advancedplus | 1.8.9-r3 | same package name |
| luci-app-diskman | 0.2.13-r1 | luci-app-diskman | 0.2.13-r3 | same package name |
| luci-app-fan | 1.0.0-r3-r1 | luci-app-fan | 1.0.0-r3 | same package name |
| luci-app-filemanager | 27.187.49110~99464ec | luci-app-filemanager | x | same package name |
| luci-app-firewall | 27.195.57574~ce598ef | luci-app-firewall | x | same package name |
| luci-app-gpsysupgrade | 27.115.44158~8a2eefa | luci-app-gpsysupgrade | x | same package name |
| luci-app-istorex | 0.6.6-r1 | luci-app-istorex | 0.6.6-r1 | same package name |
| luci-app-package-manager | 27.187.49110~99464ec | luci-app-package-manager | x | same package name |
| luci-app-partexp | 2.0.5-r4 | luci-app-partexp | 2.0.5-r4 | same package name |
| luci-app-passwall | 26.7.1-r179 | luci-app-passwall | 26.10.4-r333 | same package name |
| luci-app-quickstart | 0.12.8-r1 | luci-app-quickstart | 0.12.10-r1 | same package name |
| luci-app-store | 0.2.0-r3 | luci-app-store | 0.2.1-r1 | same package name |
| luci-app-syscontrol | 27.195.57574~ce598ef | luci-app-syscontrol | x | same package name |
| luci-app-ttyd | 26.180.75667~128a781 | luci-app-ttyd | x | same package name |
| luci-app-upnp | 27.195.57574~ce598ef | luci-app-upnp | x | same package name |
| luci-app-wifihistory | 27.195.57574~ce598ef | luci-app-wifihistory | x | same package name |
| luci-app-wizard | 27.195.57574~ce598ef | luci-app-wizard | x | same package name |
| luci-base | 27.195.57574~ce598ef | luci-base | x | same package name |
| luci-compat | 27.187.49110~99464ec | luci-compat | x | same package name |
| luci-lib-base | 27.187.49110~99464ec | luci-lib-base | x | same package name |
| luci-lib-fs | 1.0-r2 | luci-lib-fs | 1.0-r3 | same package name |
| luci-lib-ip | 27.187.49110~99464ec | luci-lib-ip | x | same package name |
| luci-lib-ipkg | 27.187.49110~99464ec | luci-lib-ipkg | x | same package name |
| luci-lib-jsonc | 27.187.49110~99464ec | luci-lib-jsonc | x | same package name |
| luci-lib-nixio | 27.187.49110~99464ec | luci-lib-nixio | x | same package name |
| luci-lib-taskd | 1.0.25-r1 | luci-lib-taskd | 1.0.26-r2 | same package name |
| luci-lib-uqr | 27.187.49110~99464ec | luci-lib-uqr | x | same package name |
| luci-lib-xterm | 4.18.0-r1 | luci-lib-xterm | 4.18.0-r1 | same package name |
| luci-lua-runtime | 27.187.49110~99464ec | luci-lua-runtime | x | same package name |
| luci-mod-admin-full | 27.187.49110~99464ec | luci-mod-admin-full | x | same package name |
| luci-mod-network | 27.195.57574~ce598ef | luci-mod-network | x | same package name |
| luci-mod-status | 27.195.57574~ce598ef | luci-mod-status | x | same package name |
| luci-mod-system | 27.195.57574~ce598ef | luci-mod-system | x | same package name |
| luci-nginx | 27.195.57574~ce598ef | luci-nginx | x | same package name |
| luci-proto-ipv6 | 27.187.49110~99464ec | luci-proto-ipv6 | x | same package name |
| luci-proto-ppp | 27.187.49110~99464ec | luci-proto-ppp | x | same package name |
| luci-theme-argon | 2.4.3-r3 | luci-theme-argon | 2.4.8-r29 | same package name |
| luci-theme-bootstrap | 27.187.49110~99464ec | luci-theme-bootstrap | x | same package name |
| lyaml | 6.2.7-r2 | lyaml | 6.2.7-r2 | same package name |
| mdadm | 4.3-r2 | mdadm | 4.3-r2 | same package name |
| microsocks | 1.0.5-r2 | microsocks | 1.0.5-r2 | same package name |
| miniupnpd-nftables | 2.3.9-r5 | miniupnpd-nftables | 2.3.9-r1 | same package name |
| mkf2fs | 1.16.0-r4 | mkf2fs | 1.16.0-r4 | same package name |
| mount-utils | 2.41.5-r1 | mount-utils | 2.41.5-r1 | same package name |
| mt7981-wo-firmware | 20260221-r1 | mt7981-wo-firmware | 20260221-r1 | same package name |
| mtd | 27 | mtd | 27 | same package name |
| my-default-settings | 2-r6 | my-default-settings | 2-r1 | same package name |
| nano | 9.1-r1 | nano | 9.0-r1 | same package name |
| netifd | 2026.02.26~cbb83a18-r1 | netifd | 2026.02.26~cbb83a1857407a28a63dc09412a1f209195914ef-r1 | same package name |
| nftables-json | 1.1.6-r2 | nftables-json | 1.1.6-r2 | same package name |
| nginx-mod-luci | 1.26.3-r4 | nginx-mod-luci | 1.26.3-r4 | same package name |
| nginx-mod-ubus | 1.26.3-r4 | nginx-mod-ubus | 1.26.3-r4 | same package name |
| nginx-ssl | 1.26.3-r4 | nginx-ssl | 1.26.3-r4 | same package name |
| nginx-ssl-util | 1.7-r2 | nginx-ssl-util | 1.7-r2 | same package name |
| ntfs3-mount | 1 | ntfs3-mount | 1 | same package name |
| odhcp6c | 2026.06.20~07d324ee-r2 | odhcp6c | 2026.06.20~07d324ee7222c0e15b9975281f18236fdccc11bd-r1 | same package name |
| odhcpd-ipv6only | 2026.06.29~5d7be43f-r1 | odhcpd-ipv6only | 2026.06.29~5d7be43f8b9dec0eb47e245cfab81108bb131273-r1 | same package name |
| openssh-sftp-server | 10.3_p1-r1 | openssh-sftp-server | 10.3_p1-r1 | same package name |
| opkg | 2025.11.05~80503d94-r1 | apk-mbedtls | 3.0.5-r3 | native 25.12 APK replacement |
| parted | 3.6-r2 | parted | 3.6-r2 | same package name |
| ppp | 2.5.2-r3 | ppp | 2.5.2-r3 | same package name |
| ppp-mod-pppoe | 2.5.2-r3 | ppp-mod-pppoe | 2.5.2-r3 | same package name |
| procd | 2026.03.13~58eb263d-r1 | procd | 2026.03.13~58eb263d5abe03f8c1280bdfa65a3b052614215d-r1 | same package name |
| procd-seccomp | 2026.03.13~58eb263d-r1 | procd-seccomp | 2026.03.13~58eb263d5abe03f8c1280bdfa65a3b052614215d-r1 | same package name |
| quickstart | 0.13.0-r5 | quickstart | 0.13.0-r5 | same package name |
| resize2fs | 1.47.3-r1 | resize2fs | 1.47.3-r1 | same package name |
| resolveip | 2 | resolveip | 2 | same package name |
| rpcd | 2026.06.04~28faf640-r1 | rpcd | 2026.06.04~28faf6403792d25b9826043aaf37880624c19568-r1 | same package name |
| rpcd-mod-file | 2026.06.04~28faf640-r1 | rpcd-mod-file | 2026.06.04~28faf6403792d25b9826043aaf37880624c19568-r1 | same package name |
| rpcd-mod-iwinfo | 2026.06.04~28faf640-r1 | rpcd-mod-iwinfo | 2026.06.04~28faf6403792d25b9826043aaf37880624c19568-r1 | same package name |
| rpcd-mod-luci | 20240305-r1 | rpcd-mod-luci | 20240305-r1 | same package name |
| rpcd-mod-rrdns | 20170710 | rpcd-mod-rrdns | 20170710 | same package name |
| rpcd-mod-ucode | 2026.06.04~28faf640-r1 | rpcd-mod-ucode | 2026.06.04~28faf6403792d25b9826043aaf37880624c19568-r1 | same package name |
| script-utils | 2.41.5-r1 | script-utils | 2.41.5-r1 | same package name |
| shadow-common | 4.19.4-r2 | shadow-common | 4.19.4-r2 | same package name |
| shadow-useradd | 4.19.4-r2 | shadow-useradd | 4.19.4-r2 | same package name |
| shadow-utils | 4.19.4-r2 | shadow-utils | 4.19.4-r2 | same package name |
| shadowsocksr-libev-ssr-local | 2.5.6-r3 | shadowsocksr-libev-ssr-local | 2.5.6-r5 | same package name |
| shadowsocksr-libev-ssr-redir | 2.5.6-r3 | shadowsocksr-libev-ssr-redir | 2.5.6-r5 | same package name |
| shellsync | 0.2-r1 | shellsync | 0.2-r1 | same package name |
| simple-obfs-client | 0.0.5-r1 | simple-obfs-client | 0.0.5-r1 | same package name |
| sing-box | 1.13.14-r22 | sing-box | 1.12.17-r1 | same package name |
| smartd | 7.5-r1 | smartd | 7.5-r1 | same package name |
| smartmontools | 7.5-r1 | smartmontools | 7.5-r1 | same package name |
| smartmontools-drivedb | 7.5-r1 | smartmontools-drivedb | 7.5-r1 | same package name |
| swconfig | 12 | swconfig | 12 | same package name |
| tar | 1.35-r1 | tar | 1.35-r1 | same package name |
| taskd | 1.0.3-r1 | taskd | 1.0.3-r1 | same package name |
| tcping | 0.3-r1 | tcping | 0.3-r1 | same package name |
| terminfo | 6.4-r3 | terminfo | 6.4-r3 | same package name |
| ttyd | 1.7.7-r1 | ttyd | 1.7.7-r1 | same package name |
| ubi-utils | 2.3.0-r1 | ubi-utils | 2.3.0-r1 | same package name |
| uboot-envtools | 2025.10-r2 | uboot-envtools | 2025.10-r2 | same package name |
| ubox | 2025.10.30~6f78fa49-r1 | ubox | 2025.10.30~6f78fa496bf36c55864a41e353df7d13f04b1077-r1 | same package name |
| ubus | 2026.06.28~24864e78-r2 | ubus | 2026.06.28~24864e7840b3a02a9ef76284a373f6b2f00b8a9b-r2 | same package name |
| ubusd | 2026.06.28~24864e78-r2 | ubusd | 2026.06.28~24864e7840b3a02a9ef76284a373f6b2f00b8a9b-r2 | same package name |
| uci | 2025.12.02~66127cd7-r1 | uci | 2025.12.02~66127cd76c5d0bd46d5a90302cc6110f53a4e2f8-r1 | same package name |
| uclient-fetch | 2026.06.07~daad21fa-r1 | uclient-fetch | 2026.06.07~daad21fa2c17cae54d37149bf27bb3dd78e50a3f-r1 | same package name |
| ucode | 2026.01.16~85922056-r1 | ucode | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-digest | 2026.01.16~85922056-r1 | ucode-mod-digest | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-fs | 2026.01.16~85922056-r1 | ucode-mod-fs | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-html | 1 | ucode-mod-html | 1 | same package name |
| ucode-mod-log | 2026.01.16~85922056-r1 | ucode-mod-log | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-lua | 1 | ucode-mod-lua | 1 | same package name |
| ucode-mod-math | 2026.01.16~85922056-r1 | ucode-mod-math | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-nl80211 | 2026.01.16~85922056-r1 | ucode-mod-nl80211 | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-rtnl | 2026.01.16~85922056-r1 | ucode-mod-rtnl | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-ubus | 2026.01.16~85922056-r1 | ucode-mod-ubus | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-uci | 2026.01.16~85922056-r1 | ucode-mod-uci | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| ucode-mod-uloop | 2026.01.16~85922056-r1 | ucode-mod-uloop | 2026.01.16~85922056ef7abeace3cca3ab28bc1ac2d88e31b1-r1 | same package name |
| urandom-seed | 3 | urandom-seed | 3 | same package name |
| urngd | 2025.10.03~f17e33d9-r1 | urngd | 2025.10.03~f17e33d9942750edbd73124e6f03118a98abb402-r1 | same package name |
| uwsgi | 2.0.30-r1 | uwsgi | 2.0.30-r1 | same package name |
| uwsgi-cgi-plugin | 2.0.30-r1 | uwsgi-cgi-plugin | 2.0.30-r1 | same package name |
| uwsgi-luci-support | 2.0.30-r1 | uwsgi-luci-support | 2.0.30-r1 | same package name |
| uwsgi-syslog-plugin | 2.0.30-r1 | uwsgi-syslog-plugin | 2.0.30-r1 | same package name |
| wget-ssl | 1.25.0-r2 | wget-ssl | 1.25.0-r2 | same package name |
| wifi-scripts | 1.0-r1 | wifi-scripts | 1.0-r1 | same package name |
| wireless-regdb | 2026.05.30-r1 | wireless-regdb | 2026.05.30-r1 | same package name |
| wpad-basic-mbedtls | 2025.08.26~ca266cc2-r2 | wpad-basic-mbedtls | 2025.08.26~ca266cc24d8705eb1a2a0857ad326e48b1408b20-r1 | same package name |
| xtables-legacy | 1.8.10-r3 | xtables-legacy | 1.8.10-r3 | same package name |
| xtables-nft | 1.8.10-r3 | xtables-nft | 1.8.10-r3 | same package name |
| xz | 5.8.1-r1 | xz | 5.8.1-r1 | same package name |
| xz-utils | 5.8.1-r1 | xz-utils | 5.8.1-r1 | same package name |
| zlib | 1.3.1-r1 | zlib | 1.3.1-r1 | same package name |
| zram-swap | 32 | zram-swap | 32 | same package name |
