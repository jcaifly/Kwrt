# The official ARM64 release is verified and packaged, not cross-executed.
include $(TOPDIR)/rules.mk

PKG_NAME:=openclash-mihomo-core
PKG_VERSION:=1.19.32
PKG_RELEASE:=1
PKG_SOURCE:=mihomo-linux-arm64-v$(PKG_VERSION).gz
PKG_SOURCE_URL:=https://github.com/MetaCubeX/mihomo/releases/download/v$(PKG_VERSION)
PKG_HASH:=9dd862e28b46ff7d775f169cceebc28deccaa0a9e804237d421cd2571e0caba0
PKG_LICENSE:=GPL-3.0-only

include $(INCLUDE_DIR)/package.mk

# Preserve the official binary byte for byte so its SHA256 remains verifiable.
RSTRIP:=:

define Package/openclash-mihomo-core
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Official Mihomo ARM64 core for OpenClash
  DEPENDS:=@aarch64 +luci-app-openclash
endef

define Build/Prepare
	$(INSTALL_DIR) $(PKG_BUILD_DIR)
	gzip -dc $(DL_DIR)/$(PKG_SOURCE) > $(PKG_BUILD_DIR)/clash_meta
	printf '%s  %s\n' c80df2ca5159567804da883401e0118908fc1155e05df2baf3dbd4d3ecfc3754 $(PKG_BUILD_DIR)/clash_meta | sha256sum -c -
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/openclash-mihomo-core/install
	$(INSTALL_DIR) $(1)/etc/openclash/core
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/clash_meta $(1)/etc/openclash/core/clash_meta
endef

$(eval $(call BuildPackage,openclash-mihomo-core))
