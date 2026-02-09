from logging import getLogger
from ssl import SSLContext

import aiohttp
from ruamel.yaml import YAML
from zabbix_utils.aioapi import AsyncZabbixAPI

from zabbixci.assets import Template

yaml = YAML()

logger = getLogger(__name__)


class ZabbixConstants:
    MINIMAL_VERSION = 6.0
    VENDOR_SUPPORTED_VERSION = 7.0
    LEGACY_SCRIPT_API_VERSION_THRESHOLD = 7.0
    TEMPLATE_GROUP_API_VERSION_THRESHOLD = 6.2


class Zabbix:
    zapi: AsyncZabbixAPI
    _client_session = None

    @property
    def api_version(self):
        return self.zapi.version

    def __init__(self, *args, **kwargs):
        if "ssl_context" in kwargs:
            if kwargs["ssl_context"]:
                if not isinstance(kwargs["ssl_context"], SSLContext):
                    raise ValueError("ssl_context must be an instance of SSLContext")

                self._client_session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=kwargs["ssl_context"])
                )

            del kwargs["ssl_context"]

        self.zapi = AsyncZabbixAPI(*args, **kwargs, client_session=self._client_session)

    def get_template_group(self, template_group_names: list[str]) -> list[dict]:
        names = template_group_names + [f"{name}/*" for name in template_group_names]

        params = {
            "search": {"name": names},
            "searchByAny": True,
            "searchWildcardsEnabled": True,
        }

        if self.api_version < ZabbixConstants.TEMPLATE_GROUP_API_VERSION_THRESHOLD:
            return self.zapi.send_sync_request("hostgroup.get", params)["result"]
        else:
            return self.zapi.send_sync_request(
                "templategroup.get",
                params,
            )["result"]

    def create_template_group(self, group_name: str):
        if self.api_version < ZabbixConstants.TEMPLATE_GROUP_API_VERSION_THRESHOLD:
            return self.zapi.send_sync_request(
                "hostgroup.create", {"name": group_name}
            )["result"]
        else:
            return self.zapi.send_sync_request(
                "templategroup.create", {"name": group_name}
            )["result"]

    def get_templates(
        self, template_group_names: list[str], filter_list: list[str] | None = None
    ):
        groups = self.get_template_group(template_group_names)

        template_group_ids = [group["groupid"] for group in groups]

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
                    **(
                        {
                            "template_groups": {
                                "createMissing": True,
                                "updateExisting": True,
                            },
                            "host_groups": {
                                "createMissing": True,
                                "updateExisting": True,
                            },
                        }
                        if self.api_version
                        >= ZabbixConstants.TEMPLATE_GROUP_API_VERSION_THRESHOLD
                        else {
                            "groups": {
                                "createMissing": True,
                                "updateExisting": True,
                            }
                        }
                    ),
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

    def get_icon_maps(self, search: list[str] | None = None):
        """
        Export icon_maps from Zabbix
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

    def update_icon_map(self, icon_map: dict):
        return self.zapi.send_sync_request("iconmap.update", icon_map)["result"]

    def create_icon_map(self, icon_map: dict):
        return self.zapi.send_sync_request("iconmap.create", icon_map)["result"]

    def delete_icon_maps(self, icon_map_ids: list[int]):
        return self.zapi.send_sync_request("iconmap.delete", icon_map_ids)["result"]

    def get_scripts(self, search: list[str] | None = None):
        """
        Export scripts from Zabbix
        """
        scripts = []

        if not search:
            scripts = self.zapi.send_sync_request("script.get", {"output": "extend"})[
                "result"
            ]
        else:
            scripts = self.zapi.send_sync_request(
                "script.get",
                {
                    "output": "extend",
                    "filter": {"name": search},
                },
            )["result"]

        if self.api_version < ZabbixConstants.LEGACY_SCRIPT_API_VERSION_THRESHOLD:
            legacy_additions = {
                "url": None,
                "new_window": None,
                "manualinput": None,
                "manualinput_prompt": None,
                "manualinput_validator": None,
                "manualinput_validator_type": None,
                "manualinput_default_value": None,
            }

            return [dict(**script, **legacy_additions) for script in scripts]

        return scripts

    def map_script(self, script: dict):
        """
        Map script object for creation or updates. mainly for handling unwanted fields for Zabbix 6.0 and earlier.

        Zabbix 6.0 only
        """
        if self.api_version >= ZabbixConstants.LEGACY_SCRIPT_API_VERSION_THRESHOLD:
            return script

        logger.debug("Mapping script object for Zabbix 6.0 compatibility.")

        default_keys = [
            "scriptid",
            "name",
            "type",
            "command",
            "scope",
            "groupid",
            "description",
        ]
        # Zabbix 6 API errors when unexpected fields were given on creation and updates. Even though these fields are returned on .get
        # Filter defines matching keys and resulting matching values, creating a ruleset for the then specified allowed fields in the form of a string list
        allowed_fields = {
            "type:authtype": {
                "2:0": ["password"],
                "2:1": ["publickey", "privatekey"],
            },
            "type": {
                "0": [
                    "execute_on",
                ],
                "2": ["authtype", "username", "port"],
                "3": ["username", "password", "port"],
                "5": ["timeout", "parameters"],
            },
            "scope": {
                "2": ["menu_path", "host_access", "confirmation", "usrgrpid"],
                "4": ["menu_path", "host_access", "confirmation", "usrgrpid"],
            },
        }

        allowed_keys = default_keys[:]

        for filter_key, filter_ruleset in allowed_fields.items():
            match_keys = filter_key.split(":")

            # For each ruleset in a key block
            for match_values_blob, rule_values in filter_ruleset.items():
                match_values = match_values_blob.split(":")

                applies = True

                # Check if all rule match keys/values apply to the script
                for key, value in zip(match_keys, match_values, strict=True):
                    if script.get(key) != value:
                        applies = False
                        break

                # This ruleset does not apply for all keys in the key:key array, try the next one
                if not applies:
                    continue

                allowed_keys.extend(rule_values)

        for key in list(script.keys()):
            if key not in allowed_keys:
                logger.debug("Deleting key %s from script object", key)
                del script[key]

        return script

    def create_script(self, script: dict):
        self.map_script(script)
        return self.zapi.send_sync_request("script.create", script)["result"]

    def update_script(self, script: dict):
        self.map_script(script)
        return self.zapi.send_sync_request("script.update", script)["result"]

    def delete_scripts(self, script_ids: list[str]):
        return self.zapi.send_sync_request("script.delete", script_ids)["result"]

    def get_user_group(self, group_name: str):
        """
        Get user group by name.
        """
        if group_name == "All":
            return {"name": "All", "usrgrpid": "0"}

        params = {
            "output": "extend",
            "filter": {"name": group_name},
        }

        return self.zapi.send_sync_request("usergroup.get", params)["result"][0]

    def get_user_group_id(self, group_id: str):
        """
        Get user group by ID.
        """
        if group_id == "0":
            return {"name": "All", "usrgrpid": "0"}

        params = {
            "usrgrpids": [group_id],
        }

        return self.zapi.send_sync_request("usergroup.get", params)["result"][0]

    def get_global_macros(self, search: list[str] | None = None):
        """
        Export global macros from Zabbix.
        """
        params: dict = {"output": "extend"}
        if search:
            params["filter"] = {"macro": search}

        try:
            return self.zapi.send_sync_request("globalmacro.get", params)["result"]
        except Exception:
            # Fallback for versions where globalmacro.* is not available
            for extra in ({"globalmacro": True}, {"globalmacros": True}):
                try:
                    return self.zapi.send_sync_request(
                        "usermacro.get",
                        {
                            **params,
                            **extra,
                        },
                    )["result"]
                except Exception:
                    continue

        return []

    def update_global_macro(self, macro: dict):
        return self.zapi.send_sync_request("usermacro.updateglobal", macro)["result"]

    def create_global_macro(self, macro: dict):
        return self.zapi.send_sync_request("usermacro.createglobal", macro)["result"]

    def delete_global_macros(self, macro_ids: list[int]):
        return self.zapi.send_sync_request("usermacro.deleteglobal", macro_ids)[
            "result"
        ]

    def get_server_version(self):
        return self.zapi.send_sync_request("apiinfo.version", need_auth=False)["result"]
