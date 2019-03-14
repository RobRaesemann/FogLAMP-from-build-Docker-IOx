import copy
import uuid
import json
import logging

from foglamp.common import logger
from foglamp.plugins.common import utils
from foglamp.services.south import exceptions

from b100.b100modbus import get_b100_readings, close_connection

""" Plugin for reading data from a B100
"""

__author__ = "Rob Raesemann, rob@raesemann.com, +1 904-613-5988"
__copyright__ = "Copyright (c) 2018 JEA"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'B100 South Service Plugin',
        'type': 'string',
        'default': 'b100',
        'readonly': 'true'
    },
    'assetName': {
        'description': 'Asset name',
        'type': 'string',
        'default': 'B100',
        'order': "1"
    },
    'pollInterval': {
        'description': 'The interval between poll calls to the device poll routine, expressed in milliseconds.',
        'type': 'integer',
        'default': '1000',
        'order': '2'
    },
    'address': {
        'description': 'Address of Modbus TCP server',
        'type': 'string',
        'default': '127.0.0.1',
        'order': '3'
    },
    'port': {
        'description': 'Port of Modbus TCP server',
        'type': 'integer',
        'default': '502',
        'order': '4'
    }
}

_LOGGER = logger.setup(__name__, level=logging.INFO)
""" Setup the access to the logging system of FogLAMP """

UNIT = 1
"""  The slave unit this request is targeting """

def plugin_info():
    """ Returns information about the plugin.

    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {
        'name': 'b100',
        'version': '1.0.0',
        'mode': 'poll',
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.

    Args:
        config: JSON configuration document for the plugin configuration category
    Returns:
        handle: JSON object to be used in future calls to the plugin
    Raises:
    """
    return copy.deepcopy(config)


def plugin_poll(handle):
    """ Poll readings from the modbus device and returns it in a JSON document as a Python dict.

    Available for poll mode only.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        returns a reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
        DataRetrievalError
    """

    try:
        source_address = handle['address']['value']
        source_port = int(handle['port']['value'])

        readings = get_b100_readings(source_address,source_port)

        wrapper = {
            'asset': handle['assetName']['value'],
            'timestamp': utils.local_timestamp(),
            'key': str(uuid.uuid4()),
            'readings': readings
        }

    except Exception as ex:
        raise exceptions.DataRetrievalError(ex)
    else:
        return wrapper


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    it should be called when the configuration of the plugin is changed during the operation of the south service.
    The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    Raises:
    """

    _LOGGER.info("Old config for B100 plugin {} \n new config {}".format(handle, new_config))

    diff = utils.get_diff(handle, new_config)

    if 'address' in diff or 'port' in diff:
        plugin_shutdown(handle)
        new_handle = plugin_init(new_config)
        new_handle['restart'] = 'yes'
        _LOGGER.info("Restarting Modbus TCP plugin due to change in configuration keys [{}]".format(', '.join(diff)))
    else:
        new_handle = copy.deepcopy(new_config)
        new_handle['restart'] = 'no'

    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup

    To be called prior to the south service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """
    try:
        return_message = close_connection()
        _LOGGER.info(return_message)
    except Exception as ex:
        _LOGGER.exception('Error in shutting down B100 plugin; %s', ex)
        raise