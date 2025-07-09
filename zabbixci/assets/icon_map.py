import logging
from typing import TextIO

from ruamel.yaml import YAML

from zabbixci.assets.asset import Asset
from zabbixci.assets.image import Image
from zabbixci.cache.cache import Cache
from zabbixci.exceptions import ZabbixIconMissingError
from zabbixci.settings import Settings

logger = logging.getLogger(__name__)
yaml = YAML()


class IconMapping:
    # Standard Zabbix dict items
    icon_mappingid: int
    icon_mapid: int
    iconid: int
    inventory_link: int
    expression: str
    sortorder: int

    # Additional items for export
    icon_map_name: str
    icon_name: str

    def __init__(
        self,
        icon_mappingid: int,
        icon_mapid: int,
        iconid: int,
        inventory_link: int,
        expression: str,
        sortorder: int,
        icon_map_name: str = "",
        icon_name: str = "",
    ):
        self.icon_mappingid = int(icon_mappingid)
        self.icon_mapid = int(icon_mapid)
        self.iconid = int(iconid)
        self.inventory_link = int(inventory_link)
        self.expression = expression
        self.sortorder = int(sortorder)
        self.icon_map_name = icon_map_name
        self.icon_name = icon_name

    @property
    def export_dict(self):
        """
        Return a dictionary representation of the IconMapping object, independent Zabbix instance.
        """
        if not self.icon_map_name or not self.icon_name:
            raise ValueError(
                "IconMapping must be exported with icon_map_name and icon_name"
            )

        return {
            "inventory_link": self.inventory_link,
            "expression": self.expression,
            "sortorder": self.sortorder,
            "iconmap_name": self.icon_map_name,
            "icon_name": self.icon_name,
        }

    @property
    def zabbix_dict(self):
        """
        Return a dictionary representation of the IconMapping object, for Zabbix API.
        """

        return {
            "iconid": self.iconid,
            "inventory_link": self.inventory_link,
            "expression": self.expression,
        }

    @classmethod
    def from_zabbix(cls, icon_mapping: dict, icon_map_name: str, images: list[Image]):
        """
        Create an IconMapping object from a Zabbix API response.

        See: https://www.zabbix.com/documentation/7.0/en/manual/api/reference/iconmap/object
        """

        icon = next(
            filter(lambda icon: icon.image_id == icon_mapping["iconid"], images), None
        )

        if not icon:
            # Unable to export icon map because iconId can not be converted to iconName
            raise ZabbixIconMissingError(
                f"Icon {icon_mapping['iconid']} not found in images, unable to export icon map"
            )

        return cls(
            icon_mapping["iconmappingid"],
            icon_mapping["iconmapid"],
            icon_mapping["iconid"],
            icon_mapping["inventory_link"],
            icon_mapping["expression"],
            icon_mapping["sortorder"],
            icon_map_name,
            icon.name,
        )


class IconMap(Asset):
    icon_mapid: int
    name: str
    default_iconid: int
    default_icon_name: str
    mappings: list[IconMapping]

    def __init__(
        self,
        icon_mapid: int,
        name: str,
        default_iconid: int,
        default_icon_name: str,
        mappings: list[IconMapping],
    ):
        self.icon_mapid = icon_mapid
        self.name = name
        self.default_iconid = default_iconid
        self.default_icon_name = default_icon_name
        self.mappings = mappings

    def __str__(self):
        return f"{self.name}"

    def _yaml_dump(self, stream: TextIO):
        yaml.dump(self.export_dict, stream)

    def save(self):
        Cache.makedirs(
            f"{Settings.CACHE_PATH}/{Settings.ICON_MAP_PREFIX_PATH}/",
        )

        with Cache.open(
            f"{Settings.CACHE_PATH}/{Settings.ICON_MAP_PREFIX_PATH}/{self.name}.yaml",
            "w",
        ) as file:
            self._yaml_dump(file)

    @property
    def export_dict(self):
        return {
            "name": self.name,
            "default_icon_name": self.default_icon_name,
            "mappings": [mapping.export_dict for mapping in self.mappings],
        }

    @property
    def zabbix_dict(self):
        return {
            "name": self.name,
            "default_iconid": str(self.default_iconid),
            "mappings": [mapping.zabbix_dict for mapping in self.mappings],
        }

    @classmethod
    def from_zabbix(cls, icon_map: dict, icons: list[Image]):
        """
        Create an IconMap object from a Zabbix API response.

        See: https://www.zabbix.com/documentation/7.0/en/manual/api/reference/iconmap/object#icon-map

        :param icon_map: Zabbix API response
        :param icons: List of Image

        :return: IconMap object or None when the object could not be created
        """
        mappings = [
            IconMapping.from_zabbix(mapping, icon_map["name"], icons)
            for mapping in icon_map["mappings"]
        ]

        mappings.sort(key=lambda x: x.sortorder)

        icon = next(
            filter(lambda icon: icon.image_id == icon_map["default_iconid"], icons),
            None,
        )

        if not icon:
            # Unable to export icon map because defaultIconId can not be converted to defaultIconName
            raise ZabbixIconMissingError(
                f"Icon {icon_map['default_iconid']} not found in images, unable to export icon map"
            )

        return cls(
            icon_map["iconmapid"],
            icon_map["name"],
            icon_map["default_iconid"],
            icon.name,
            mappings,
        )

    @classmethod
    def partial_open(cls, path: str):
        """
        Load an IconMap object from a file. Without Zabbix instance mappings (ids)
        """
        with Cache.open(path, "r") as file:
            icon_map = yaml.load(file)

            return cls(
                0,
                icon_map["name"],
                0,
                icon_map["default_icon_name"],
                [],
            )

    @classmethod
    def open(cls, path: str, images: list[Image]):
        """
        Load an IconMap object from a file.
        """
        with Cache.open(path, "r") as file:
            icon_map = yaml.load(file)

            default_icon = next(
                filter(lambda icon: icon.name == icon_map["default_icon_name"], images),
                None,
            )

            # Unable to import a icon_map without matching icon names to ids of current Zabbix server
            if not default_icon or not default_icon.image_id:
                raise ZabbixIconMissingError(
                    f"Icon {icon_map['default_icon_name']} not found in images, unable to import icon map"
                )

            def icon_mapping(mapping, images: list[Image]):
                icon = next(
                    filter(lambda icon: icon.name == mapping["icon_name"], images),
                    None,
                )

                if not icon or not icon.image_id:
                    raise ValueError(f"Icon {mapping['icon_name']} not found in images")

                return IconMapping(
                    0,
                    0,
                    icon.image_id,
                    mapping["inventory_link"],
                    mapping["expression"],
                    mapping["sortorder"],
                    icon_map["name"],
                    mapping["icon_name"],
                )

            return cls(
                0,
                icon_map["name"],
                default_icon.image_id,
                icon_map["default_icon_name"],
                [icon_mapping(mapping, images) for mapping in icon_map["mappings"]],
            )
