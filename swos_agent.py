#!/usr/bin/env python3
# Shebang needed only for editors
#
# Path: ~/local/lib/python3/cmk_addons/plugins/swos/rulesets/swos_agent.py
#
# Rule "MikroTik SwOS switch" (Setup > Agents > Other integrations).
# Every element maps 1:1 to an option of libexec/agent_swos; an element that is
# not configured is simply not passed, and the agent uses its built-in default.

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    DictGroup,
    Float,
    InputHint,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import MatchRegex
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

# Anchored on purpose: MatchRegex may use match, search or fullmatch semantics.
_PORT_LIST = r"\s*\d+(?:\s*-\s*\d+)?(?:\s*,\s*\d+(?:\s*-\s*\d+)?)*\s*"
_PORTS_OR_ALL = rf"^(?:\s*(?i:all)\s*|{_PORT_LIST})$"
_PORTS_ONLY = rf"^{_PORT_LIST}$"
_MAC = r"^\s*(?:[0-9A-Fa-f]{2}[:-]?){5}[0-9A-Fa-f]{2}\s*$"

_CONNECTION = DictGroup(title=Title("Connection"))
_SCOPE = DictGroup(title=Title("What to monitor"))
_PORTS = DictGroup(title=Title("Ports"))
_HEALTH = DictGroup(title=Title("Health: temperature, fans, power supplies"))
_POE = DictGroup(title=Title("PoE"))
_SFP = DictGroup(title=Title("SFP / QSFP modules"))
_STP = DictGroup(title=Title("Spanning tree"))

_CHECK_GROUPS = (
    ("system", "System information and uptime"),
    ("temp", "Temperatures"),
    ("fans", "Fans"),
    ("psu", "Power supplies"),
    ("ports", "Ports (link, speed, duplex, flow control, RSTP, LAG, PoE)"),
    ("stats", "Traffic, packet and error rates on the port services"),
    ("sfp", "SFP / QSFP modules"),
    ("poe", "PoE total power"),
    ("rstp", "Spanning tree (RSTP)"),
    ("lag", "Link aggregation (LAG)"),
)


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("MikroTik SwOS switch"),
        help_text=Help(
            "Queries the web interface of a MikroTik SwOS switch and creates services for "
            "system data, temperatures, fans, power supplies, ports (with traffic and error "
            "rates), SFP modules, PoE, spanning tree and link aggregation. Assign this rule "
            "to the host that represents the switch."
        ),
        elements={
            # ---- connection ---------------------------------------------------
            "host": DictElement(
                group=_CONNECTION,
                parameter_form=String(
                    title=Title("Switch address (override)"),
                    help_text=Help(
                        "Address or host name the switch is reached at. By default the IP "
                        "address of the host this rule applies to is used."
                    ),
                ),
            ),
            "user": DictElement(
                group=_CONNECTION,
                parameter_form=String(
                    title=Title("User name"),
                    help_text=Help("Default: admin"),
                    prefill=DefaultValue("admin"),
                ),
            ),
            "password": DictElement(
                group=_CONNECTION,
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help(
                        "Password of the switch's web interface. Leave unset for the SwOS "
                        "factory login (empty password). On Checkmk 2.5 and later the "
                        "password is handed over as a password-store reference; on older "
                        "versions it appears in the process list while the agent runs."
                    ),
                ),
            ),
            "timeout": DictElement(
                group=_CONNECTION,
                parameter_form=Integer(
                    title=Title("HTTP timeout"),
                    help_text=Help("Applies to every request to the switch. Default: 10 seconds."),
                    unit_symbol="seconds",
                    prefill=DefaultValue(10),
                ),
            ),
            "piggyback": DictElement(
                group=_CONNECTION,
                parameter_form=String(
                    title=Title("Piggyback host name"),
                    help_text=Help(
                        "Deliver the services to another Checkmk host as piggyback data. "
                        "Normally unset: the services belong to the host this rule applies to."
                    ),
                ),
            ),
            "state_dir": DictElement(
                group=_CONNECTION,
                parameter_form=String(
                    title=Title("State directory"),
                    help_text=Help(
                        "Where counter snapshots are kept to compute traffic and error rates "
                        "between two runs. Default: var/check_mk/agent_swos in the site."
                    ),
                ),
            ),
            # ---- scope --------------------------------------------------------
            "checks": DictElement(
                group=_SCOPE,
                parameter_form=MultipleChoice(
                    title=Title("Monitored groups"),
                    help_text=Help(
                        "Default: everything. If nothing is selected, everything is monitored."
                    ),
                    elements=[
                        MultipleChoiceElement(name=name, title=Title(text))
                        for name, text in _CHECK_GROUPS
                    ],
                    show_toggle_all=True,
                    prefill=DefaultValue([name for name, _ in _CHECK_GROUPS]),
                ),
            ),
            "ports": DictElement(
                group=_SCOPE,
                parameter_form=String(
                    title=Title("Ports that get a service"),
                    help_text=Help(
                        "A list such as 1-8,49-52, or 'all' (default). Also limits the SFP "
                        "services, which are matched by port number."
                    ),
                    prefill=InputHint("all"),
                    custom_validate=(
                        MatchRegex(
                            _PORTS_OR_ALL,
                            error_msg=Message("Enter 'all' or a list of ports such as 1-8,49,50."),
                        ),
                    ),
                ),
            ),
            # ---- ports --------------------------------------------------------
            "expected_up": DictElement(
                group=_PORTS,
                parameter_form=String(
                    title=Title("Ports that must be up"),
                    help_text=Help(
                        "Uplinks, servers, access points... A down port is CRIT only if it is "
                        "listed here; all other ports are OK when down. Example: 1,49-50"
                    ),
                    prefill=InputHint("1,49-50"),
                    custom_validate=(
                        MatchRegex(
                            _PORTS_ONLY,
                            error_msg=Message("Enter a list of ports such as 1-8,49,50."),
                        ),
                    ),
                ),
            ),
            "min_speed": DictElement(
                group=_PORTS,
                parameter_form=Integer(
                    title=Title("Minimum speed of ports that must be up"),
                    help_text=Help(
                        "WARN if such a port negotiates a lower speed. Not configured or 0: off."
                    ),
                    unit_symbol="Mbit/s",
                    prefill=DefaultValue(1000),
                ),
            ),
            "error_warn": DictElement(
                group=_PORTS,
                parameter_form=Integer(
                    title=Title("WARN at new port errors"),
                    help_text=Help(
                        "WARN when a port counted at least this many new errors (FCS, runts, "
                        "jabber, overruns, underruns, late/excessive collisions) since the "
                        "previous run. 0 switches the check off. Default: 1."
                    ),
                    unit_symbol="errors",
                    prefill=DefaultValue(1),
                ),
            ),
            # ---- health -------------------------------------------------------
            "temp_warn": DictElement(
                group=_HEALTH,
                parameter_form=Float(
                    title=Title("Temperature: WARN at"),
                    help_text=Help(
                        "CPU, board, PHY and PSU temperatures. Default: 75 °C. These defaults "
                        "are placeholders: MikroTik does not publish limits, so adjust them."
                    ),
                    unit_symbol="°C",
                    prefill=DefaultValue(75.0),
                ),
            ),
            "temp_crit": DictElement(
                group=_HEALTH,
                parameter_form=Float(
                    title=Title("Temperature: CRIT at"),
                    help_text=Help("Default: 90 °C."),
                    unit_symbol="°C",
                    prefill=DefaultValue(90.0),
                ),
            ),
            "fan_count": DictElement(
                group=_HEALTH,
                parameter_form=Integer(
                    title=Title("Number of installed fans"),
                    help_text=Help(
                        "The switch always reports four fans, even if it has fewer, and a "
                        "stopped fan looks the same as a missing one. Say how many really "
                        "exist so that a stopped fan becomes CRIT. Not configured: fans "
                        "reading 0 RPM are hidden."
                    ),
                    unit_symbol="fans",
                    prefill=InputHint(4),
                ),
            ),
            "fan_min_rpm": DictElement(
                group=_HEALTH,
                parameter_form=Integer(
                    title=Title("Fan speed: CRIT below"),
                    help_text=Help("Not configured or 0: off."),
                    unit_symbol="RPM",
                    prefill=DefaultValue(1000),
                ),
            ),
            "psu_count": DictElement(
                group=_HEALTH,
                parameter_form=Integer(
                    title=Title("Number of installed power supplies"),
                    help_text=Help(
                        "Same reasoning as for fans: a failed power supply looks like an empty "
                        "slot. Say how many are installed so that a failure becomes CRIT."
                    ),
                    unit_symbol="power supplies",
                    prefill=InputHint(2),
                ),
            ),
            "psu_voltage_scale": DictElement(
                group=_HEALTH,
                parameter_form=Float(
                    title=Title("Power supply voltage divisor"),
                    help_text=Help(
                        "The raw value is divided by this number to get volts. 100 is verified "
                        "on the CRS354; other models may report millivolts, which needs 1000. "
                        "Default: 100."
                    ),
                    prefill=DefaultValue(100.0),
                ),
            ),
            # ---- PoE ----------------------------------------------------------
            "poe": DictElement(
                group=_POE,
                parameter_form=SingleChoice(
                    title=Title("PoE data"),
                    help_text=Help(
                        "Automatic uses the PoE page if the switch has one. Default: automatic."
                    ),
                    elements=[
                        SingleChoiceElement(name="auto", title=Title("Automatic")),
                        SingleChoiceElement(name="yes", title=Title("Required (error if missing)")),
                        SingleChoiceElement(name="no", title=Title("Ignore PoE")),
                    ],
                    prefill=DefaultValue("auto"),
                ),
            ),
            "poe_total_warn": DictElement(
                group=_POE,
                parameter_form=Float(
                    title=Title("Total PoE power: WARN at"),
                    help_text=Help("Not configured: no threshold."),
                    unit_symbol="W",
                    prefill=InputHint(400.0),
                ),
            ),
            "poe_total_crit": DictElement(
                group=_POE,
                parameter_form=Float(
                    title=Title("Total PoE power: CRIT at"),
                    help_text=Help("Not configured: no threshold."),
                    unit_symbol="W",
                    prefill=InputHint(550.0),
                ),
            ),
            # ---- SFP ----------------------------------------------------------
            "sfp_temp_warn": DictElement(
                group=_SFP,
                parameter_form=Float(
                    title=Title("Module temperature: WARN at"),
                    help_text=Help("Default: 70 °C."),
                    unit_symbol="°C",
                    prefill=DefaultValue(70.0),
                ),
            ),
            "sfp_temp_crit": DictElement(
                group=_SFP,
                parameter_form=Float(
                    title=Title("Module temperature: CRIT at"),
                    help_text=Help("Default: 85 °C."),
                    unit_symbol="°C",
                    prefill=DefaultValue(85.0),
                ),
            ),
            "sfp_rx_dbm_warn": DictElement(
                group=_SFP,
                parameter_form=Float(
                    title=Title("Rx power: WARN below"),
                    help_text=Help("Low-light alert. Not configured: no threshold."),
                    unit_symbol="dBm",
                    prefill=InputHint(-14.0),
                ),
            ),
            "sfp_rx_dbm_crit": DictElement(
                group=_SFP,
                parameter_form=Float(
                    title=Title("Rx power: CRIT below"),
                    help_text=Help("Not configured: no threshold."),
                    unit_symbol="dBm",
                    prefill=InputHint(-18.0),
                ),
            ),
            # ---- spanning tree -------------------------------------------------
            "rstp_root": DictElement(
                group=_STP,
                parameter_form=String(
                    title=Title("Expected root bridge (MAC address)"),
                    help_text=Help(
                        "WARN if the spanning-tree root bridge is a different device. Not "
                        "configured: the root bridge is shown but not checked."
                    ),
                    label=Label("MAC"),
                    prefill=InputHint("48:8f:5a:05:6f:5d"),
                    custom_validate=(
                        MatchRegex(_MAC, error_msg=Message("Enter a MAC address.")),
                    ),
                ),
            ),
        },
    )


rule_spec_swos = SpecialAgent(
    name="swos",
    title=Title("MikroTik SwOS switch"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    help_text=Help("Monitors a MikroTik SwOS switch through its web interface."),
)
