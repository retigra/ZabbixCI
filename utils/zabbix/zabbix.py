from zabbix_utils import ZabbixAPI
from typing import ParamSpec
from ruamel.yaml import YAML
from io import StringIO

yaml = YAML()

P = ParamSpec('P')


class Zabbix():
    zapi = None

    def __init__(self, *args: P.args, **kwargs: P.kwargs):
        self.zapi = ZabbixAPI(*args, **kwargs)

    def get_templates(self, tags: list[dict] = None):
        if tags is None:
            tags = [
                {
                    "tag": "retigra",
                    "value": "true"
                }
            ]

        return self.zapi.send_api_request(
            "template.get",
            {
                "tags": tags
            }
        )['result']

    def export_template(self, template_ids: list[int]):
        return self.zapi.send_api_request(
            "configuration.export",
            {
                "options": {
                    "templates": template_ids
                },
                "format": "yaml"
            }
        )['result']

    def import_template(self, template: dict):
        reconstructed_export = StringIO()

        yaml.dump({
            "zabbix_export": {
                "templates": [template],
                "version": template.pop('synchronization_zabbix_version')
            }
        }, reconstructed_export)

        with open("./tests/export.yaml", "w") as file:
            file.write(reconstructed_export.getvalue())

        return self.zapi.send_api_request(
            "configuration.import",
            {
                "format": "yaml",
                "rules": {
                    "templates": {
                        "createMissing": True,
                        "updateExisting": True
                    }
                },
                "source": reconstructed_export.getvalue()
            }
        )['result']
