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
        return self._template["name"]

    @property
    def uuid(self):
        return self._template["uuid"]

    @property
    def template_id(self):
        return self._template["templateid"]

    @property
    def template_ids(self):
        return [template["templateid"] for template in self._export["templates"]]

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
            if not Settings.ROOT_TEMPLATE_GROUP in name:
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

    def __init__(self, export: dict):
        self._export = export

    def __str__(self):
        return self._template["name"]

    def _yaml_dump(self, stream: TextIO):
        """
        Dump Zabbix importable template to stream
        """
        yaml.dump({"zabbix_export": self._export}, stream)

    def save(self):
        """
        Save the template to the cache
        """
        os.makedirs(
            f"{Settings.CACHE_PATH}/{Settings.TEMPLATE_PREFIX_PATH}/{self.truncated_groups}",
            exist_ok=True,
        )

        with open(
            f"{Settings.CACHE_PATH}/{Settings.TEMPLATE_PREFIX_PATH}/{self.truncated_groups}/{self._template['name']}.yaml",
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
