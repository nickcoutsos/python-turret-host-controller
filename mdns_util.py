from pybonjour import (
    kDNSServiceFlagsAdd,
    DNSServiceProcessResult as process_result,
    DNSServiceBrowse as browse_dns_services,
    DNSServiceResolve as resolve_dns_service,
    DNSServiceRegister as register_dns_service
)

def _process_callback(ref):
    def callback(fd, events):
        process_result(ref)
    return callback

class MDNS(object):

    def __init__(self, ioloop):
        self._ioloop = ioloop
        self._broadcast_refs = {}
        self._discovery_refs = {}
        self._resolution_refs = {}

    def _handle_ref(self, ref):
        self._ioloop.add_handler(
            ref.fileno(),
            _process_callback(ref),
            self._ioloop.READ)

    def _close_ref(self, ref):
        pass


    def register(self, name, regtype, domain, port):
        """
        Broadcast the existence of this service.
        """

        ref = register_dns_service(
            name=name,
            regtype=regtype,
            domain=domain,
            port=port)

        self._handle_ref(ref)
        self._broadcast_refs[name + regtype + domain + str(port)] = ref

    def unregister(self, name, regtype, domain, port):
        """
        Stop broadcasting the existence of this service.
        """

        ref_key = name + regtype + domain + str(port)
        ref = self._broadcast_refs.get(ref_key, None)
        if not ref:
            return

        del self._broadcast_refs[ref_key]
        self._ioloop.remove_handler(ref.fileno())
        ref.close()

    def discover(self, regtype, on_discovered, on_lost):
        """
        Notify listener when a service is found/lost.
        """

        if regtype in self._discovery_refs:
            return

        resolution_refs = self._resolution_refs[regtype] = []

        def resolve_callback(ref, flags, index, error, fullname, host, port, txtRecord):
            on_discovered(index, fullname, host, port, txtRecord)

        def browse_callback(ref, flags, index, error, name, regtype, domain):
            if flags & kDNSServiceFlagsAdd:
                resolution_ref = resolve_dns_service(0, index, name, regtype, domain, resolve_callback)
                resolution_refs.append(resolution_ref)
                self._handle_ref(resolution_ref)
            else:
                on_lost(index, name, regtype, domain)

        browse_ref = browse_dns_services(regtype=regtype, callBack=browse_callback)

        self._handle_ref(browse_ref)
        self._discovery_refs[regtype] = browse_ref

    def disable_discovery(self, regtype):
        """
        Stop looking for services of the given regtype and close handlers.
        """

        if regtype not in self._discovery_refs:
            return

        browse_ref = self._discovery_refs[regtype]

        self._ioloop.remove_handler(browse_ref.fileno())
        browse_ref.close()

        for resolution_ref in self._resolution_refs[regtype]:
            self._ioloop.remove_handler(resolution_ref.fileno())
            resolution_ref.close()

        del self._discovery_refs[regtype]
        del self._resolution_refs[regtype]