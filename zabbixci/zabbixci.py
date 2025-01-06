import logging
import os
from io import StringIO

from ruamel.yaml import YAML

from zabbixci.settings import Settings
from zabbixci.utils.template import Template
from zabbixci.utils.zabbix import Zabbix

logger = logging.getLogger(__name__)
yaml = YAML()


def ignore_template(template_name: str) -> bool:
    """
    Returns true if template should be ignored because of the blacklist or whitelist
    """
    if template_name in Settings.BLACKLIST:
        logger.debug(f"Skipping blacklisted template {template_name}")
        return True

    if len(Settings.WHITELIST) and template_name not in Settings.WHITELIST:
        logger.debug(f"Skipping non whitelisted template {template_name}")
        return True

    return False


def cleanup_cache(full: bool = False) -> None:
    """
    Clean all .yaml (template) files from the cache directory

    If full is True, also remove the .git directory and all other files
    """
    for root, dirs, files in os.walk(
        f"{Settings.CACHE_PATH}/{Settings.GIT_PREFIX_PATH}", topdown=False
    ):
        if f"{Settings.CACHE_PATH}/.git" in root and not full:
            continue

        for name in files:
            if name.endswith(".yaml") or full:
                os.remove(os.path.join(root, name))

        for name in dirs:
            if name == ".git" and root == Settings.CACHE_PATH and not full:
                continue

            # Remove empty directories
            if not os.listdir(os.path.join(root, name)):
                os.rmdir(os.path.join(root, name))

    if full:
        os.rmdir(Settings.CACHE_PATH)
        logger.info("Cache directory cleared")


def zabbix_to_file(zabbix: Zabbix) -> None:
    """
    Export Zabbix templates to the cache
    """
    templates = zabbix.get_templates([Settings.PARENT_GROUP])

    logger.info(f"Found {len(templates)} templates in Zabbix")
    logger.debug(f"Found Zabbix templates: {templates}")

    # Split by Settings.BATCH_SIZE
    batches = [
        templates[i : i + Settings.BATCH_SIZE]
        for i in range(0, len(templates), Settings.BATCH_SIZE)
    ]

    for index, batch in enumerate(batches):
        logger.info(
            f"Processing export batch {index + 1}/{len(batches)} [{(index * Settings.BATCH_SIZE) + 1}/{len(templates)}]"
        )

        # Get the templates
        template_yaml = zabbix.export_template(
            [template["templateid"] for template in batch]
        )

        export_yaml = yaml.load(StringIO(template_yaml))

        if not "templates" in export_yaml["zabbix_export"]:
            logger.info("No templates found in Zabbix")
            return

        # Write the templates to the cache
        for template in export_yaml["zabbix_export"]["templates"]:
            template = Template.from_zabbix(
                template,
                export_yaml["zabbix_export"]["template_groups"],
                export_yaml["zabbix_export"]["version"],
            )

            if ignore_template(template.name):
                continue

            template.save()
