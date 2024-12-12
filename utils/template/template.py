from ruamel.yaml import YAML
from settings import CACHE_PATH
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
        selected_group = ""
        selected_length = 0

        # Most specific group is based on the group with the most slashes, specifying the lowest child in the hierarchy
        for group in self._template['groups']:
            name: str = group['name']

            split = regex.split(r'\/+', name)

            if len(split) > selected_length:
                selected_group = name
                selected_length = len(split)

        return selected_group

    def __init__(self, export: dict):
        self._export = export

    def __str__(self):
        return self._template['name']

    def save(self):
        """
        Save the template to the cache
        """
        os.makedirs(f"{CACHE_PATH}/{self.primary_group}", exist_ok=True)

        with open(f"{CACHE_PATH}/{self.primary_group}/{self._template['name']}.yaml", "w") as file:
            yaml.dump(self._export, file)

    def export(self):
        """
        Export the template as Zabbix importable YAML
        """
        return yaml.dump(self._template)

    @staticmethod
    def open(name: str):
        """
        Open a template from the cache
        """
        with open(f"{CACHE_PATH}/{name}.yaml", "r") as file:
            return Template(yaml.load(file))

    @staticmethod
    def from_zabbix(template: dict, template_groups: dict, zabbix_version: str):
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
