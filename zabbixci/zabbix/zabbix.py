from ssl import SSLContext

import aiohttp
from ruamel.yaml import YAML
from zabbix_utils import AsyncZabbixAPI

from zabbixci.assets import Template

yaml = YAML()


class Zabbix:
    zapi: AsyncZabbixAPI
    _client_session = None

    def __init__(self, *args, **kwargs):
        if "ssl_context" in kwargs:
            if kwargs["ssl_context"] and isinstance(kwargs["ssl_context"], SSLContext):
                self._client_session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=kwargs["ssl_context"])
                )
            else:
                raise ValueError("ssl_context must be an SSLContext object")

            del kwargs["ssl_context"]

        self.zapi = AsyncZabbixAPI(*args, **kwargs, client_session=self._client_session)

    def _get_template_group(self, template_group_names: list[str]):
        return self.zapi.send_sync_request(
            "templategroup.get", {"search": {"name": template_group_names}}
        )["result"]

    def get_templates(
        self, template_group_names: list[str], filter_list: list[str] | None = None
    ):
        ids = self._get_template_group(template_group_names)

        template_group_ids = [group["groupid"] for group in ids]

        if filter_list:
            return self.zapi.send_sync_request(
                "template.get",
                {"groupids": template_group_ids, "filter": {"host": filter_list}},
            )["result"]
        else:
            return self.zapi.send_sync_request(
                "template.get", {"groupids": template_group_ids}
            )["result"]

    def set_template(self, template_id: int, changes: dict):
        return self.zapi.send_sync_request(
            "template.update", {"templateid": template_id, **changes}
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
                    "templateDashboards": {
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

    def get_templates_name(self, name: list[str]):
        return self.zapi.send_sync_request("template.get", {"filter": {"host": name}})[
            "result"
        ]

    def delete_templates(self, template_ids: list[int]):
        return self.zapi.send_sync_request("template.delete", template_ids)["result"]

    def get_images(self, search: list[str] | None = None):
        """
        Export images from Zabbix

        TODO: Add batching for large number of images
        """
        if not search:
            return self.zapi.send_sync_request(
                "image.get", {"output": "extend", "select_image": True}
            )["result"]
        else:
            return self.zapi.send_sync_request(
                "image.get",
                {"output": "extend", "select_image": True, "filter": {"name": search}},
            )["result"]

    def create_image(self, image: dict):
        return self.zapi.send_sync_request("image.create", image)["result"]

    def update_image(self, image: dict):
        return self.zapi.send_sync_request("image.update", image)["result"]

    def delete_images(self, image_ids: list[int]):
        return self.zapi.send_sync_request("image.delete", image_ids)["result"]

    def get_iconmaps(self, search: list[str] | None = None):
        """
        Export iconmaps from Zabbix
        """
        if not search:
            return self.zapi.send_sync_request(
                "iconmap.get", {"output": "extend", "selectMappings": "extend"}
            )["result"]
        else:
            return self.zapi.send_sync_request(
                "iconmap.get",
                {
                    "output": "extend",
                    "selectMappings": "extend",
                    "filter": {"name": search},
                },
            )["result"]

    def update_iconmap(self, iconmap: dict):
        return self.zapi.send_sync_request("iconmap.update", iconmap)["result"]

    def create_iconmap(self, iconmap: dict):
        return self.zapi.send_sync_request("iconmap.create", iconmap)["result"]

    def delete_iconmaps(self, iconmap_ids: list[int]):
        return self.zapi.send_sync_request("iconmap.delete", iconmap_ids)["result"]

    def get_server_version(self):
        return self.zapi.send_sync_request("apiinfo.version", need_auth=False)["result"]
