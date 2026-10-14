include $(TOPDIR)/rules.mk

PKG_NAME:=my-default-settings
PKG_VERSION:=2
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define Package/my-default-settings
  SECTION:=luci
  CATEGORY:=LuCI
  TITLE:=Audited defaults for this RAX3000M vendor package rebuild
  DEPENDS:=+luci-base
  PKGARCH:=all
endef

define Build/Prepare
endef
define Build/Configure
endef
define Build/Compile
endef

define Package/my-default-settings/install
	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./defaults $(1)/etc/uci-defaults/zz-rax3000m-vendor
endef

$(eval $(call BuildPackage,my-default-settings))
