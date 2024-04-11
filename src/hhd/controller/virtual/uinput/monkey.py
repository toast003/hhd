from evdev import UInput, _uinput, ecodes  # type: ignore
import ctypes


# Monkey patch Uinput device to avoid issues
# _find_device() may crash when controllers
# disconnect. We dont use the produced device anyway.
def _patch(*args, **kwargs):
    pass


UInput._find_device = _patch


def _new_init(
    self,
    events=None,
    name="py-evdev-uinput",
    vendor=0x1,
    product=0x1,
    version=0x1,
    bustype=0x3,
    devnode="/dev/uinput",
    phys="py-evdev-uinput",
    input_props=None,
    uniq=None,
):

    self.name = name  #: Uinput device name.
    self.vendor = vendor  #: Device vendor identifier.
    self.product = product  #: Device product identifier.
    self.version = version  #: Device version identifier.
    self.bustype = bustype  #: Device bustype - e.g. ``BUS_USB``.
    self.phys = phys  #: Uinput device physical path.
    self.devnode = devnode  #: Uinput device node - e.g. ``/dev/uinput/``.

    if not events:
        events = {ecodes.EV_KEY: ecodes.keys.keys()}  # type: ignore

    self._verify()

    #: Write-only, non-blocking file descriptor to the uinput device node.
    self.fd = _uinput.open(devnode)

    # Prepare the list of events for passing to _uinput.enable and _uinput.setup.
    absinfo, prepared_events = self._prepare_events(events)

    # Set phys name
    _uinput.set_phys(self.fd, phys)

    # Set properties
    input_props = input_props or []
    for prop in input_props:
        _uinput.set_prop(self.fd, prop)

    for etype, code in prepared_events:
        _uinput.enable(self.fd, etype, code)

    _uinput.setup(self.fd, name, vendor, product, version, bustype, absinfo)

    if uniq:
        from fcntl import ioctl
        from ...lib.ioctl import UI_SET_UNIQ_STR

        c_uniq = ctypes.create_string_buffer(uniq.encode())
        ioctl(self.fd, UI_SET_UNIQ_STR(len(c_uniq)), c_uniq, False)

    # Create the uinput device.
    _uinput.create(self.fd)

    self.dll = ctypes.CDLL(_uinput.__file__)
    self.dll._uinput_begin_upload.restype = ctypes.c_int
    self.dll._uinput_end_upload.restype = ctypes.c_int

    self.device = None


UInput.__init__ = _new_init
