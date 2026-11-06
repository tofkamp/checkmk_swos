Monitor Mikrotik SwOS routers

Querying the web interface of the device to monitor:

- System information and uptime
- Temperatures
- Fans
- Power supplies
- Ports (link, speed, duplex, flow control, RSTP, LAG, PoE)
- Traffic, packet and error rates on the port services
- SFP / QSFP modules
- PoE total power
- Spanning tree (RSTP)
- Link aggregation (LAG)

### Installation

Install the `.mkp` file via **Setup → Extension packages** or via the CLI:

```
mkp install swos-<version>.mkp
```
Alternative install
```
sudo bash
su monitoring     # su <sitename>
cd ~/local/lib/python3/cmk_addons/plugins
tar xvf /tmp/swos_checkmk_plugin.tar.gz
```
After installation, configure the special agent under
**Setup → Other integrations → MikroTik SwOS** and assign it to your
MikroTik hosts.

Issues and source [https://github.com/tofkamp/checkmk\_swos](https://github.com/tofkamp/checkmk_swos)

Compatibility SWoS/Release
|       | v2.18 | v2.19 |   |   |
|-------|-------|-------|---|---|
| 1.0.0 | &#x2713; |   &#x2713;   |   |   |


Actively used in production with the following models:
- CRS354-48P-4S+2Q+
- CRS326-24S+2Q+

If you tested the monitoring on another device type, please report this.

---
## Checkmk agent plugin for MikroTik SwOS switches
```
Polls ONE SwOS switch per run over HTTP (digest auth) and prints the result as
Checkmk <<<local>>> checks. Optionally the output is wrapped as piggyback data
for another host name (--piggyback / SWOS_PIGGYBACK).
Only dependency: the Python "requests" module.

Runs as a Checkmk special agent (plug-in family "swos": this file belongs in
libexec/agent_swos, see rulesets/ and server_side_calls/) or standalone.

Services (field names/scales were taken from the web UI JavaScript
of a real CRS354-48P-4S+2Q+ running SwOS 2.18):

  SwOS System         identity, model, version, serial, MAC, IP, build, uptime
  SwOS Temp <sensor>  CPU / board 1 / board 2 / PHY temperature
  SwOS Fan <n>        fan RPM
  SwOS PSU <n>        status, voltage, current, power, temperature
  SwOS Port NN        link, speed, duplex, flow control, RSTP role/state, LAG,
                      PoE, traffic rates, packet rates, errors
  SwOS SFP NN         module info + DDM (temperature, voltage, bias, Tx/Rx dBm)
  SwOS PoE Total      total PoE draw
  SwOS RSTP           bridge/root bridge, port roles
  SwOS LAG <n>        trunk members and partner
  SwOS API            reachability and response time

Configuration, one switch per run. Every option exists twice:
  environment variable  SWOS_<OPTION>   (e.g. SWOS_HOST, SWOS_TEMP_WARN)
  command-line option   --<option>      (e.g. --host, --temp-warn; underscores
                                         become dashes, see --help)
Command-line options win. Checkmk can only hand over command-line arguments, so
the agent exports them into its own environment and reads everything from there.
The address of the switch (host / SWOS_HOST) is required. Unset or empty values
fall back to the GLOBAL SETTINGS just below.

The password is --password (plain text; visible in the process list) or, on
Checkmk >= 2.5, --password-id (a password-store reference, resolved here).
SWOS_PASSWORD still works for standalone use.

Test:    SWOS_HOST=192.168.88.2 SWOS_PASSWORD=secret ./agent_swos
         ./agent_swos --host 192.168.88.2 --user admin --expected-up 1,49
         ./agent_swos --host 192.168.88.2 --dump       raw decoded pages

```
