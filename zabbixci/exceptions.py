class BaseZabbixCIException(Exception):
    pass


class GitException(BaseZabbixCIException):
    pass


class ZabbixException(BaseZabbixCIException):
    pass


class ZabbixIconMissingException(ZabbixException):
    pass
