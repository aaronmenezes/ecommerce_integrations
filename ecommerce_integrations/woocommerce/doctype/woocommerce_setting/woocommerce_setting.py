# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.model.document import Document
from frappe.utils.nestedset import get_root_of
from urllib.parse import urlparse

from ecommerce_integrations.patches.update_woocommerce_items import create_ecommerce_items
from ecommerce_integrations.woocommerce.constants import PRODUCT_GROUP


class WoocommerceSetting(Document):
	def validate(self):
		self.validate_settings()
		self.create_delete_custom_fields()
		self.create_webhook_url()
		if self.enable_sync:
			create_ecommerce_items()

	def create_delete_custom_fields(self):
		if self.enable_sync:
			for doctype in ["Customer", "Sales Order", "Item", "Address"]:
				df = dict(
					fieldname="woocommerce_id",
					label="Woocommerce ID",
					fieldtype="Data",
					read_only=1,
					print_hide=1,
				)
				create_custom_field(doctype, df)

			for doctype in ["Customer", "Address"]:
				df = dict(
					fieldname="woocommerce_email",
					label="Woocommerce Email",
					fieldtype="Data",
					read_only=1,
					print_hide=1,
				)
				create_custom_field(doctype, df)

			sku_dict = dict(fieldname="sku", label="SKU", fieldtype="Data", read_only=1, print_hide=1,)
			create_custom_field("Item", sku_dict)

			if not frappe.get_value("Item Group", {"name": PRODUCT_GROUP}):
				item_group = frappe.new_doc("Item Group")
				item_group.item_group_name = PRODUCT_GROUP
				item_group.parent_item_group = get_root_of("Item Group")
				item_group.insert(ignore_mandatory=True)

	def validate_settings(self):
		if self.enable_sync:
			if not self.secret:
				self.set("secret", frappe.generate_hash())

			if not self.woocommerce_server_url:
				frappe.throw(_("Please enter Woocommerce Server URL"))

			if not self.api_consumer_key:
				frappe.throw(_("Please enter API Consumer Key"))

			if not self.api_consumer_secret:
				frappe.throw(_("Please enter API Consumer Secret"))

	def create_webhook_url(self):

		endpoint = "/api/method/ecommerce_integrations.woocommerce.woocommerce_connection.order"

		try:
			if frappe.conf.developer_mode and frappe.conf.localtunnel_url:
				url = frappe.conf.localtunnel_url
			else:
				url = frappe.request.url
		except RuntimeError:
			url = "http://localhost:8000"

		server_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(url))

		delivery_url = server_url + endpoint
		self.endpoint = delivery_url


@frappe.whitelist()
def generate_secret():
	woocommerce_settings = frappe.get_doc("Woocommerce Setting")
	woocommerce_settings.secret = frappe.generate_hash()
	woocommerce_settings.save()


@frappe.whitelist()
def get_series():
	return {
		"sales_order_series": frappe.get_meta("Sales Order").get_options("naming_series") or "SO-WOO-",
	}
