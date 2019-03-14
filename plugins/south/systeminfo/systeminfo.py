# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Module for System Info async plugin """

import copy
import uuid
import subprocess

from foglamp.common import logger
from foglamp.plugins.common import utils

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'System info async plugin',
        'type': 'string',
        'default': 'systeminfo',
        'readonly': 'true'
    },
    'assetNamePrefix': {
        'description': 'Asset prefix',
        'type': 'string',
        'default': "system/",
        'order': "1",
        'displayName': 'Asset Name Prefix'
    },
}
_LOGGER = logger.setup(__name__, level=logger.logging.INFO)


def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {
        'name': 'System Info plugin',
        'version': '1.5.0',
        'mode': 'poll',
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.
    Args:
        config: JSON configuration document for the South device configuration category
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """
    data = copy.deepcopy(config)
    return data


def plugin_poll(handle):
    """ Extracts data from the system info and returns it in a JSON document as a Python dict.
    Available for async mode only.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        a system info reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
        TimeoutError
    """
    readings = []

    def get_subprocess_result(cmd):
        a = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs, errs = a.communicate()
        if a.returncode != 0:
            raise OSError(
                'Error in executing command "{}". Error: {}'.format(cmd, errs.decode('utf-8').replace('\n', '')))
        d = [b for b in outs.decode('utf-8').split('\n') if b != '']
        return d

    def get_system_info(time_stamp):
        data = {}

        # Get hostname
        hostname = get_subprocess_result(cmd='hostname')[0]
        insert_reading("hostName", time_stamp, {"hostName": hostname})

        # Get platform info
        platform = get_subprocess_result(cmd='cat /proc/version')[0]
        insert_reading("platform", time_stamp, {"platform": platform})

        # Get uptime
        uptime_secs = get_subprocess_result(cmd='cat /proc/uptime')[0].split()
        uptime = {
                "system_seconds": float(uptime_secs[0].strip()),
                "idle_processes_seconds": float(uptime_secs[1].strip()),
        }
        insert_reading("uptime", time_stamp, uptime)

        # Get load average
        line_load = get_subprocess_result(cmd='cat /proc/loadavg')[0].split()
        load_average = {
                "overLast1min": float(line_load[0].strip()),
                "overLast5mins": float(line_load[1].strip()),
                "overLast15mins": float(line_load[2].strip())
        }
        insert_reading("loadAverage", time_stamp, load_average)

        # Get processes count
        tasks_states = get_subprocess_result(cmd="ps -e -o state")
        processes = {
                "running": tasks_states.count("R"),
                "sleeping": tasks_states.count("S") + tasks_states.count("D"),
                "stopped": tasks_states.count("T") + tasks_states.count("t"),
                "paging": tasks_states.count("W"),
                "dead": tasks_states.count("X"),
                "zombie": tasks_states.count("Z")
            }
        insert_reading("processes", time_stamp, processes)

        # Get CPU usage
        c3_mpstat = get_subprocess_result(cmd='mpstat')
        cpu_usage = {}
        col_heads = c3_mpstat[1].split()  # first line is the header row
        start_index = col_heads.index("CPU") + 1
        for line in c3_mpstat[2:]:  # second line onwards are value rows
            col_vals = line.split()
            for i in range(start_index, len(col_vals)):
                cpu_usage[col_heads[i].replace("%", "prcntg_")] = float(col_vals[i].strip())
            insert_reading("cpuUsage_"+col_vals[start_index-1], time_stamp, cpu_usage)

        # Get memory info
        c3_mem = get_subprocess_result(cmd='cat /proc/meminfo')
        mem_info = {}
        for line in c3_mem:
            line_a = line.split(':')
            line_vals = line_a[1].split()
            k = "{}{}".format(line_a[0], '_KB' if len(line_vals) > 1 else '').replace("(","").replace(")","").strip()
            v = int(line_vals[0].strip())
            mem_info.update({k : v})
        insert_reading("memInfo", time_stamp, mem_info)

        # Get disk usage
        c3_all = get_subprocess_result(cmd='df -l')

        # On some systems, errors are reported by df command, hence we need to filter those lines first
        c3_temp1 = get_subprocess_result(cmd='df -l | grep -n Filesystem')
        c3_temp2 = c3_temp1[0].split("Filesystem")
        c3_start = int(c3_temp2[0].strip().replace(":", "")) - 1
        c3 = c3_all[c3_start:]

        col_heads = c3[0].split()  # first line is the header row
        for line in c3[1:]:  # second line onwards are value rows
            col_vals = line.split()
            disk_usage = {}
            for i in range(1, len(col_vals)):
                disk_usage[col_heads[i].replace("%", "_prcntg")] = int(col_vals[i].replace("%", "").strip()) if i < len(col_vals)-1 else col_vals[i]
            dev_key = (col_vals[0])[1:] if col_vals[0].startswith('/') else col_vals[0]  # remove starting / from /dev/sda5 etc
            insert_reading("diskUsage_"+dev_key, time_stamp, disk_usage)

        # Get Network and other info
        c3_net = get_subprocess_result(cmd='cat /proc/net/dev')
        col_heads = c3_net[1].replace("|", " ").split()
        for i in range(len(col_heads)):
            col_heads[i] = "{}_{}".format("Receive" if i <= 8 else "Transmit", col_heads[i].strip())
        col_heads[0] = "Interface"
        for line in c3_net[2:]:
            line_a = line.replace(":", " ").split()
            interface_name = line_a[0].strip()
            net_info = {}
            for i in range(1, len(line_a)):
                net_info.update({col_heads[i]: line_a[i]})
            insert_reading("networkTraffic_"+interface_name, time_stamp, net_info)

        # Paging and Swapping
        c6 = get_subprocess_result(cmd='vmstat -s')
        paging_swapping = {}
        for line in c6:
            if 'page' in line:
                a_line = line.strip().split("pages")
                paging_swapping.update({a_line[1].replace(' ', ''): int(a_line[0].strip())})
        insert_reading("pagingAndSwappingEvents", time_stamp, paging_swapping)

        # Disk Traffic
        c4 = get_subprocess_result(cmd='iostat -xd 2 1')
        c5 = [i for i in c4[1:] if i.strip() != '']  # Remove all empty lines
        col_heads = c5[0].split()  # first line is header row
        for line in c5[1:]:  # second line onwards are value rows
            col_vals = line.split()
            disk_traffic = {}
            for i in range(1, len(col_vals)):
                disk_traffic[col_heads[i].replace("%", "prcntg_").replace("/s", "_per_sec")] = float(col_vals[i].strip())
            insert_reading("diskTraffic_"+col_vals[0], time_stamp, disk_traffic)

        return data

    def insert_reading(asset, time_stamp, data):
        data = {
            'asset': "{}{}".format(handle['assetNamePrefix']['value'], asset),
            'timestamp': time_stamp,
            'key': str(uuid.uuid4()),
            'readings': data
        }
        readings.append(data)
    try:
        time_stamp = utils.local_timestamp()
        get_system_info(time_stamp)
    except (OSError, Exception, RuntimeError) as ex:
        _LOGGER.exception("System Info exception: {}".format(str(ex)))
        raise ex
    return readings


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    it should be called when the configuration of the plugin is changed during the operation of the South device service;
    The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    Raises:
    """
    _LOGGER.info("Old config for systeminfo plugin {} \n new config {}".format(handle, new_config))
    new_handle = copy.deepcopy(new_config)
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the South device service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    """
    _LOGGER.info('system info plugin shut down.')