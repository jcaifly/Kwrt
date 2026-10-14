include $(TOPDIR)/rules.mk

PKG_NAME:=luci-lib-fs
PKG_VERSION:=1.0
PKG_RELEASE:=3
PKG_LICENSE:=Apache-2.0

include $(INCLUDE_DIR)/package.mk

define Package/luci-lib-fs
  SECTION:=luci
  CATEGORY:=LuCI
  TITLE:=Legacy LuCI filesystem compatibility library
  DEPENDS:=+luci-lib-nixio +luci-compat
  PKGARCH:=all
endef

define Build/Prepare
endef
define Build/Configure
endef
define Build/Compile
endef

define Package/luci-lib-fs/install
	$(INSTALL_DIR) $(1)/usr/lib/lua/luci
	$(INSTALL_DATA) ./fs.lua $(1)/usr/lib/lua/luci/fs.lua
endef

$(eval $(call BuildPackage,luci-lib-fs))
