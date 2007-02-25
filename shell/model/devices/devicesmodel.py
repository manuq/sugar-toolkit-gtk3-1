import gobject

from model.devices import device
from model.devices import wirednetwork
from model.devices import wirelessnetwork
from model.devices import battery
from hardware import hardwaremanager
from hardware import nmclient

class DevicesModel(gobject.GObject):
    __gsignals__ = {
        'device-appeared'   : (gobject.SIGNAL_RUN_FIRST,
                               gobject.TYPE_NONE, 
                              ([gobject.TYPE_PYOBJECT])),
        'device-disappeared': (gobject.SIGNAL_RUN_FIRST,
                               gobject.TYPE_NONE, 
                              ([gobject.TYPE_PYOBJECT]))
    }
   
    def __init__(self):
        gobject.GObject.__init__(self)

        self._devices = []
        self.add_device(battery.Device())

        self._observe_network_manager()

    def _observe_network_manager(self):
        network_manager = hardwaremanager.get_network_manager()

        for device in network_manager.get_devices():
            self._check_network_device(device)

        network_manager.connect('device-activated',
                                self._network_device_added_cb)

    def _network_device_added_cb(self, network_manager, device):
        self._check_network_device(device)

    def _check_network_device(self, device):
        if not device.is_valid():
            return

        if device.get_type() == nmclient.DEVICE_TYPE_802_11_WIRELESS:
            self.add_device(wirelessnetwork.Device(device))
           
    def __iter__(self):
        return iter(self._devices)

    def add_device(self, device):
        self._devices.append(device)
        self.emit('device-appeared', device)
