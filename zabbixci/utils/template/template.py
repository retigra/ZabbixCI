import logging
import os
from io import StringIO
from typing import TextIO

import regex
from ruamel.yaml import YAML

from zabbixci.settings import Settings

yaml = YAML()

logger = logging.getLogger(__name__)


class Template:
    """
    A Python representation of a Zabbix template
    """

    _export: dict
    _level: int = None

    new_version = False
    new_vendor = False

    @property
    def is_template(self):
        return "templates" in self._export

    @property
    def _template(self):
        return self._export["templates"][0]

    @property
    def groups(self):
        return map(lambda group: group["name"], self._template["groups"])

    @property
    def name(self):
        return self._template["template"]

    @property
    def uuid(self):
        return self._template["uuid"]

    @property
    def template_id(self):
        return self._template["templateid"]

    @property
    def template_ids(self):
        return [template["uuid"] for template in self._export["templates"]]

    @property
    def primary_group(self):
        """
        The most specific group of the template, the lowest child in the hierarchy
        """
        selected_group = self._template["groups"][0]["name"]
        selected_length = 0

        # Most specific group is based on the group with the most slashes,
        # specifying the lowest child in the hierarchy
        for group in self._template["groups"]:
            name: str = group["name"]
            if Settings.ROOT_TEMPLATE_GROUP not in name:
                continue

            split = regex.split(r"\/+", name)

            if len(split) > selected_length:
                selected_group = name
                selected_length = len(split)

        return selected_group

    @property
    def truncated_groups(self):
        """
        The primary group of the template, without the root group
        """
        # split = regex.split(fr'{PARENT_GROUP}\/+', self.primary_group)
        match_group = regex.match(
            rf"{Settings.ROOT_TEMPLATE_GROUP}\/+(.+)", self.primary_group
        )

        return match_group.group(1) if match_group else ""

    @property
    def linked_templates(self):
        return (
            [t["name"] for t in self._template["templates"]]
            if "templates" in self._template
            else []
        )

    @property
    def zabbix_version(self):
        return self._export["version"]

    @property
    def vendor(self):
        if "vendor" not in self._template:
            return ""

        return (
            self._template["vendor"]["name"]
            if "name" in self._template["vendor"]
            else ""
        )

    @property
    def version(self):
        if "vendor" not in self._template:
            return ""

        return (
            self._template["vendor"]["version"]
            if "version" in self._template["vendor"]
            else ""
        )

    @property
    def updated_items(self):
        """
        dict containg the new vendor and or version
        """
        updates = {}

        if self.new_vendor:
            updates["vendor_name"] = self.vendor

        if self.new_version:
            updates["vendor_version"] = self.version

        return updates

    def __init__(self, export: dict):
        self._export = export

    def __str__(self):
        return self._template["name"]

    def _yaml_dump(self, stream: TextIO):
        """
        Dump Zabbix importable template to stream
        """
        yaml.dump({"zabbix_export": self._export}, stream)

    def _insert_vendor_dict(self):
        """
        Insert vendor dict into export.
        Vendor needs to be positioned after description
        to match the Zabbix export format
        """
        description_index = list(self._template.keys()).index("description")

        items = list(self._template.items())
        items.insert(description_index + 1, ("vendor", {}))
        self._export["templates"][0] = dict(items)

    def set_vendor(self, vendor: str):
        """
        Set the vendor of the template
        """
        if "vendor" not in self._export["templates"][0]:
            self._insert_vendor_dict()

        self._export["templates"][0]["vendor"]["name"] = vendor
        self.new_vendor = True

    def set_version(self, version: str):
        """
        Set the version of the template
        """
        if "vendor" not in self._export["templates"][0]:
            self._insert_vendor_dict()

        self._export["templates"][0]["vendor"]["version"] = version
        self.new_version = True

    def save(self):
        """
        Save the template to the cache
        """
        os.makedirs(
            f"{Settings.CACHE_PATH}/{Settings.TEMPLATE_PREFIX_PATH}/{self.truncated_groups}",
            exist_ok=True,
        )

        with open(
            f"{Settings.CACHE_PATH}/{Settings.TEMPLATE_PREFIX_PATH}/{self.truncated_groups}/{self._template['template']}.yaml",
            "w",
        ) as file:
            self._yaml_dump(file)

    def export(self):
        """
        Export the template as Zabbix importable YAML
        """
        stream = StringIO()
        self._yaml_dump(stream)
        return stream.getvalue()

    def level(self, templates: list):
        """
        Get the amount of linked levels
        """
        logger.debug(f"Getting level for {self.name}")

        linked_templates = [t for t in templates if t.name in self.linked_templates]

        self._level = (
            max([template.level(templates) for template in linked_templates] or [0]) + 1
        )

        return self._level

    @staticmethod
    def open(path: str):
        """
        Open a template from the cache
        """
        with open(f"{Settings.CACHE_PATH}/{path}", "r") as file:
            return Template(yaml.load(file)["zabbix_export"])

    @staticmethod
    def from_zabbix(export: dict):
        """
        Create a individual template from a bulk Zabbix export
        """
        # TODO: Prepare dict for export, otherwise remove this method and use the constructor directly

        return Template(export)
