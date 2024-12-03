from zabbix_utils import ZabbixAPI
from typing import ParamSpec

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
