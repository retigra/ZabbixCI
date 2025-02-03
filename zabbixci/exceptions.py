class BaseZabbixCIException(Exception):
    pass


class GitException(BaseZabbixCIException):
    pass


class ZabbixException(BaseZabbixCIException):
    pass
