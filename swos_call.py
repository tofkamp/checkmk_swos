#!/usr/bin/env python3
# Shebang needed only for editors
#
# Path: ~/local/lib/python3/cmk_addons/plugins/swos/server_side_calls/swos_call.py
#
# Turns the rule "MikroTik SwOS switch" into the command line of libexec/agent_swos.
#
# Why command-line arguments and not environment variables: SpecialAgentCommand
# only accepts `command_arguments` and `stdin`; there is no way to set environment
# variables for the call. agent_swos therefore takes every setting as a command-line
# option and exports it into its own environment (SWOS_<OPTION>) on startup.

from collections.abc import Iterator, Mapping

from cmk.server_side_calls.v1 import (
    HostConfig,
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)

try:  # Checkmk >= 2.5.0: the agent can resolve a password-store reference itself
    import cmk.password_store.v1_unstable  # noqa: F401

    _PASSWORD_STORE_API = True
except ImportError:
    _PASSWORD_STORE_API = False

# Rule element -> agent option (--<name with dashes>). Values are passed as
# --name=value, which also keeps negative numbers such as -14.0 unambiguous.
_PLAIN_OPTIONS = (
    "user",
    "timeout",
    "piggyback",
    "state_dir",
    "ports",
    "expected_up",
    "min_speed",
    "error_warn",
    "temp_warn",
    "temp_crit",
    "fan_count",
    "fan_min_rpm",
    "psu_count",
    "psu_voltage_scale",
    "poe",
    "poe_total_warn",
    "poe_total_crit",
    "sfp_temp_warn",
    "sfp_temp_crit",
    "sfp_rx_dbm_warn",
    "sfp_rx_dbm_crit",
    "rstp_root",
)


def _address(host_config: HostConfig) -> str:
    """IP address of the host, or its name (resolved by DNS) if it has none."""
    ip_config = getattr(host_config, "primary_ip_config", None)
    address = getattr(ip_config, "address", None) if ip_config is not None else None
    return str(address or host_config.name)


def _swos_commands(
    params: Mapping[str, object], host_config: HostConfig
) -> Iterator[SpecialAgentCommand]:
    args: list = ["--host=%s" % (params.get("host") or _address(host_config))]

    for key in _PLAIN_OPTIONS:
        value = params.get(key)
        if value is not None and value != "":
            args.append("--%s=%s" % (key.replace("_", "-"), value))

    checks = params.get("checks")
    if checks:  # an empty selection means "everything", which is the agent default
        args.append("--checks=%s" % ",".join(str(c) for c in checks))

    password = params.get("password")
    if password is not None:
        if _PASSWORD_STORE_API:
            args += ["--password-id", password]  # reference, resolved inside the agent
        else:
            args += ["--password", password.unsafe()]  # plain text on the command line

    yield SpecialAgentCommand(command_arguments=args)


special_agent_swos = SpecialAgentConfig(
    name="swos",
    parameter_parser=noop_parser,
    commands_function=_swos_commands,
)
