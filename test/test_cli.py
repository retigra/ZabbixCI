from unittest import TestCase

from zabbixci.cli import read_args
from zabbixci.settings import Settings


class TestCLI(TestCase):
    def test_cli_true(self) -> None:

        items = dict(Settings.__dict__).items()

        for key, value in items:
            if not key.isupper() or key.startswith("_"):
                continue

            arguments: list[str] = []

            arguments.append(f"--{key.lower().replace('_', '-')}")

            is_bool = isinstance(value, bool)
            is_int = isinstance(value, int)
            is_str = isinstance(value, str)

            expected_value: tuple[str | None, int | str | bool] = ("", "")

            if is_bool:
                expected_value = (None, True)
            elif is_int:
                expected_value = (
                    "1",
                    "1",
                )  # It seems the cli parser doesn't convert the value to int
            elif is_str or not value:
                expected_value = ("test", "test")

            if expected_value[0]:
                arguments.append(expected_value[0])

            arguments.append("push")

            # Read args
            args = read_args(arguments)
            parsed_args = vars(args)

            # Update settings
            for dkey, dvalue in parsed_args.items():
                if dvalue is not None:
                    setattr(Settings, dkey.upper(), dvalue)

            # Test if setting is updated
            self.assertEqual(
                Settings.__dict__[key], expected_value[1], f"Failed for {key}"
            )
