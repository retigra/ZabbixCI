from typing import ParamSpec

import aiohttp
from ruamel.yaml import YAML
from zabbix_utils import AsyncZabbixAPI

from zabbixci.utils.template import Template

yaml = YAML()

P = ParamSpec("P")


class Zabbix:
    zapi = None
    _client_session = None

    def __init__(self, *args: P.args, **kwargs: P.kwargs):

        if "ssl_context" in kwargs:
            if kwargs["ssl_context"]:
                self._client_session = aiohttp.ClientSession()
                self._client_session._connector._ssl = kwargs["ssl_context"]

            del kwargs["ssl_context"]

        self.zapi = AsyncZabbixAPI(*args, **kwargs, client_session=self._client_session)

    def _get_template_group(self, template_group_names: list[str]):
        return self.zapi.send_sync_request(
            "templategroup.get", {"search": {"name": template_group_names}}
        )["result"]

    def get_templates(self, template_group_names: list[str]):
        ids = self._get_template_group(template_group_names)

        template_group_ids = [group["groupid"] for group in ids]

        return self.zapi.send_sync_request(
            "template.get", {"groupids": template_group_ids}
        )["result"]

    def export_template_async(self, template_ids: list[int]):
        return self.zapi.send_async_request(
            "configuration.export",
            {"options": {"templates": template_ids}, "format": "yaml"},
        )

    def import_template(self, template: Template):
        export = template.export()

        return self.zapi.send_sync_request(
            "configuration.import",
            {
                "format": "yaml",
                "rules": {
                    "template_groups": {"createMissing": True, "updateExisting": True},
                    "templateLinkage": {"createMissing": True, "deleteMissing": True},
                    "templates": {
                        "createMissing": True,
                        "updateExisting": True,
                    },
                    "discoveryRules": {
                        "createMissing": True,
                        "updateExisting": True,
                        "deleteMissing": True,
                    },
                    "graphs": {
                        "createMissing": True,
                        "updateExisting": True,
                        "deleteMissing": True,
                    },
                    "httptests": {
                        "createMissing": True,
                        "updateExisting": True,
                        "deleteMissing": True,
                    },
                    "items": {
                        "createMissing": True,
                        "updateExisting": True,
                        "deleteMissing": True,
                    },
                    "triggers": {
                        "createMissing": True,
                        "updateExisting": True,
                        "deleteMissing": True,
                    },
                    "valueMaps": {
                        "createMissing": True,
                        "updateExisting": True,
                        "deleteMissing": True,
                    },
                },
                "source": export,
            },
        )["result"]

    def get_server_version(self):
        return self.zapi.send_sync_request("apiinfo.version", need_auth=False)["result"]

    def get_templates_name(self, name: list[str]):
        return self.zapi.send_sync_request("template.get", {"filter": {"host": name}})[
            "result"
        ]

    def delete_template(self, template_ids: list[int]):
        return self.zapi.send_sync_request("template.delete", template_ids)["result"]
