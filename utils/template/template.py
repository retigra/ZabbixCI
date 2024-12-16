from io import StringIO
from typing import TextIO
from ruamel.yaml import YAML
from settings import CACHE_PATH, PARENT_GROUP
import regex
import os

yaml = YAML()


class Template:
    """
    A Python representation of a Zabbix template
    """
    _export: dict

    @property
    def _template(self):
        return self._export['templates'][0]

    @property
    def groups(self):
        return map(lambda group: group['name'], self._template['groups'])

    @property
    def primary_group(self):
        """
        The most specific group of the template, the lowest child in the hierarchy
        """
        selected_group = self._template['groups'][0]['name']
        selected_length = 0

        # Most specific group is based on the group with the most slashes,
        # specifying the lowest child in the hierarchy
        for group in self._template['groups']:
            name: str = group['name']
            if not PARENT_GROUP in name:
                continue

            split = regex.split(r'\/+', name)

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
            fr'{PARENT_GROUP}\/+(.+)', self.primary_group)

        return match_group.group(1) if match_group else self.primary_group

    def __init__(self, export: dict):
        self._export = export

    def __str__(self):
        return self._template['name']

    def _yaml_dump(self, stream: TextIO):
        """
        Dump Zabbix importable template to stream
        """
        yaml.dump({
            "zabbix_export": self._export
        }, stream)

    def save(self):
        """
        Save the template to the cache
        """
        os.makedirs(f"{CACHE_PATH}/{self.truncated_groups}", exist_ok=True)

        with open(f"{CACHE_PATH}/{self.truncated_groups}/{self._template['name']}.yaml", "w") as file:
            self._yaml_dump(file)

    def export(self):
        """
        Export the template as Zabbix importable YAML
        """
        stream = StringIO()
        self._yaml_dump(stream)
        return stream.getvalue()

    @staticmethod
    def open(path: str):
        """
        Open a template from the cache
        """
        with open(f"{CACHE_PATH}/{path}", "r") as file:
            return Template(yaml.load(file)['zabbix_export'])

    @staticmethod
    def from_zabbix(template: dict, template_groups: dict,
                    zabbix_version: str):
        """
        Create a individual template from a bulk Zabbix export
        """
        groups = list(
            filter(
                lambda group: group['name'] in [group['name']
                                                for group in template['groups']], template_groups
            )
        )

        return Template({
            'version': zabbix_version,
            'template_groups': groups,
            'templates': [template]
        })
