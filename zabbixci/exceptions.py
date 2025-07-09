class BaseZabbixCIError(Exception):
    pass


class GitError(BaseZabbixCIError):
    pass


class ZabbixError(BaseZabbixCIError):
    pass


class ZabbixIconMissingError(ZabbixError):
    pass
