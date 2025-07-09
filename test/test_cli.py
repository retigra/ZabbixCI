from unittest import TestCase

from zabbixci.cli import read_args
from zabbixci.settings import Settings

# Setting keys that are not available as CLI arguments
IGNORED_KEYS_CLI = ["ZABBIX_KWARGS", "GIT_KWARGS", "ACTION"]


def test_cli_arg(
    key: str, value, test_value: str
) -> tuple[str | None, int | str | bool] | None:
    if not key.isupper() or key.startswith("_") or key in IGNORED_KEYS_CLI:
        return None

    arguments: list[str] = []

    # Add value for the current key
    expected_value: tuple[str | None, int | str | bool] = ("", "")
    if isinstance(value, bool):
        arguments.append(
            f"--{key.lower().replace('_', '-')}{f'={test_value}' if test_value == 'false' else ''}"
        )
        expected_value = (
            None,
            test_value == "true",
        )
    elif isinstance(value, int):
        arguments.append(f"--{key.lower().replace('_', '-')}")
        expected_value = (test_value, test_value)
    elif isinstance(value, str) or not value:
        arguments.append(f"--{key.lower().replace('_', '-')}")
        expected_value = (test_value, test_value)
    if expected_value[0]:
        arguments.append(expected_value[0])

    # Add push
    arguments.append("push")

    try:
        # Read args
        args = read_args(arguments)
        parsed_args = vars(args)
    except SystemExit:
        print(f"Failed for: {arguments}")  # noqa: T201

    # Update settings
    for dkey, dvalue in parsed_args.items():
        if dvalue is not None:
            setattr(Settings, dkey.upper(), dvalue)

    return expected_value


class TestCLI(TestCase):
    def setUp(self):
        self.settings_backup = Settings.__dict__.copy()

    def test_cli_0(self) -> None:
        items = dict(Settings.__dict__).items()
        for key, value in items:
            expected_value = test_cli_arg(key, value, "true")

            if not expected_value:
                continue

            # Test if setting is updated
            self.assertEqual(
                Settings.__dict__[key], expected_value[1], f"Failed for {key}"
            )

    def test_cli_1(self) -> None:
        items = dict(Settings.__dict__).items()
        for key, value in items:
            expected_value = test_cli_arg(key, value, "false")

            if not expected_value:
                continue

            # Test if setting is updated
            self.assertEqual(
                Settings.__dict__[key], expected_value[1], f"Failed for {key}"
            )

    def tearDown(self):
        # Restore settings
        for key, value in self.settings_backup.items():
            if not key.isupper() or key.startswith("_") or key == "ACTION":
                continue
            setattr(Settings, key, value)
