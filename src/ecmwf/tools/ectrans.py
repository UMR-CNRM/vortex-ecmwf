"""
System Addons to support ECMWF' EcTrans data transfert tool.
"""

import logging

import footprints
from vortex.config import from_config
from vortex.tools import addons
from vortex.tools.systems import fmtshcmd

from .interfaces import ECtrans

#: No automatic export
__all__ = []

LOG = logging.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the ECtrans interface defined by optional arguments."""
    kw["shell"] = sh
    return footprints.proxy.addon(**kw)


class ECtransError(Exception):
    """Generic ECtrans error"""

    pass


class ECtransConfigurationError(ECtransError):
    """Generic ECtrans configuration error"""

    pass


class ECtransTools(addons.Addon):
    """
    Handle ECtrans use properly within Vortex.
    """

    _footprint = dict(
        info="Default ECtrans system interface",
        attr=dict(
            kind=dict(
                values=["ectrans"],
            ),
        ),
    )

    def ectrans_gateway_init(self, gateway=None):
        """Initialize the gateway attribute used by ECtrans.

        :param gateway: gateway used if provided
        :return: the gateway to be used by ECtrans
        """
        if gateway is not None:
            return gateway

        return from_config("ectrans", "gateway")

    def ectrans_remote_init(self, remote=None, storage=None):
        """Initialize the remote attribute used by Ectrans.

        :param remote: remote used if provided
        :param storage: the store place
        :return: the remote to be used by ECtrans
        """
        if remote is not None:
            return remote

        if storage is None:
            storage = "default"

        return from_config("ectrans", f"remote_{storage}")

    @staticmethod
    def ectrans_defaults_init(**kwargs):
        """Initialise the default for ECtrans.

        :return: the different structures used by the ECtrans interface initialised
        """
        sync = kwargs.pop("sync", True)
        list_args = list()
        dict_args = dict()
        list_options = list()
        for k, v in kwargs.items():
            if isinstance(v, bool) and v:
                list_options.append(k)
            else:
                dict_args[k] = v
        if sync:
            dict_args.setdefault("priority", 80)
            dict_args.setdefault("retryCnt", 0)
        else:
            dict_args.setdefault("priority", 30)
            dict_args.setdefault("retryCnt", 72)  # Retry for 12 hours
            dict_args.setdefault("retryFrq", 600)  # 10 minutes between tries
        if "verbose" not in kwargs:
            list_options.append("verbose")
        if "overwrite" not in kwargs:
            list_options.append("overwrite")
        return list_args, list_options, dict_args

    def raw_ectransput(
        self, source, target, gateway=None, remote=None, sync=False, **kwargs
    ):
        """Put a resource using ECtrans (default class).

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param bool sync: If False, allow asynchronous transfers.
        :return: return code
        """
        ectrans = ECtrans(system=self.sh)
        list_args, list_options, dict_args = self.ectrans_defaults_init(
            sync=sync, **kwargs
        )
        if sync:
            list_options.append("put")
        dict_args["gateway"] = gateway
        dict_args["remote"] = remote
        dict_args["source"] = source
        dict_args["target"] = target
        rc = ectrans(
            list_args=list_args, list_options=list_options, dict_args=dict_args
        )
        return rc

    @fmtshcmd
    def ectransput(
        self,
        source,
        target,
        gateway=None,
        remote=None,
        cpipeline=None,
        sync=False,
    ):
        """Put a resource using ECtrans.

        This class is not used if a particular method format_ectransput exists.

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline used if provided
        :param bool sync: If False, allow asynchronous transfers.
        :return: return code
        """
        if self.sh.is_iofile(source):
            if cpipeline is None:
                rc = self.raw_ectransput(
                    source=source,
                    target=target,
                    gateway=gateway,
                    remote=remote,
                    sync=sync,
                )
            else:
                csource = self.sh.safe_fileaddsuffix(source)
                try:
                    cpipeline.compress2file(source=source, destination=csource)
                    rc = self.raw_ectransput(
                        source=csource,
                        target=target,
                        gateway=gateway,
                        remote=remote,
                        sync=sync,
                    )
                finally:
                    self.sh.rm(csource)
        else:
            raise OSError("No such file or directory: {!r}".format(source))
        return rc

    def raw_ectransget(self, source, target, gateway, remote):
        """Get a resource using ECtrans (default class).

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :return: return code
        """
        ectrans = ECtrans(system=self.sh)
        list_args, list_options, dict_args = self.ectrans_defaults_init()
        list_options.append("get")
        dict_args["gateway"] = gateway
        dict_args["remote"] = remote
        dict_args["source"] = source
        dict_args["target"] = target
        rc = ectrans(
            list_args=list_args, list_options=list_options, dict_args=dict_args
        )
        return rc

    @fmtshcmd
    def ectransget(
        self, source, target, gateway=None, remote=None, cpipeline=None
    ):
        """Get a resource using ECtrans.

        This class is not used if a particular method format_ectransput exists.

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used if provided
        :return: return code
        """
        if isinstance(target, str):
            self.sh.rm(target)
        if cpipeline is None:
            rc = self.raw_ectransget(
                source=source, target=target, gateway=gateway, remote=remote
            )
        else:
            ctarget = self.sh.safe_fileaddsuffix(target)
            try:
                rc = self.raw_ectransget(
                    source=source,
                    target=ctarget,
                    gateway=gateway,
                    remote=remote,
                )
                rc = rc and cpipeline.file2uncompress(
                    source=ctarget, destination=target
                )
            finally:
                self.sh.rm(ctarget)
        return rc
