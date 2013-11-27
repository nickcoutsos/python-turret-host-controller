import logging
import tornado.ioloop
import tornado.web
import sys

import mdns_util

class ConfigurationHandler(tornado.web.RequestHandler):
    def get(self):
        self.finish({})

class HostsHandler(tornado.web.RequestHandler):
    def get(self):
        self.finish({
            'connected_hosts': [],
            'visible_hosts': []
        })

    def delete(self):
        pass

class TurretsHandler(tornado.web.RequestHandler):
    def get(self):
        self.finish({
            'active_turrets': [],
            'known_turrets': []
        })

def create_service():

    app = tornado.web.Application([
        (r'/configuration/?', ConfigurationHandler),
        (r'/hosts/?', HostsHandler),
        (r'/turrets/?', TurretsHandler),
    ])

    logger = logging.getLogger('thcsvc')
    logger.setLevel(logging.DEBUG)
    app.logger = logger

    return app

def run_service(port, address='0.0.0.0', configuration=None):
    ioloop = tornado.ioloop.IOLoop.instance()
    app = create_service()
    app.listen(port, address)
    app.logger.info('Started THC service on %s:%s', address, port)

    def discovered_service(index, fullname, host, port, txtRecord):
        app.logger.info('Found service: %s@%s:%s', fullname, host, port)

    def lost_service(index, name, regtype, domain):
        app.logger.info('Lost service: %s.%s@%s', name, regtype, domain)

    app.mdns = mdns_util.MDNS(ioloop)
    app.mdns.register('TurretHostController', '_thc_http._tcp', 'local', port)
    app.logger.info('Registered THC service.')

    app.mdns.discover('_thc_http._tcp', discovered_service, lost_service)
    app.logger.info('Listening for neighboring services.')


    try:
        ioloop.start()
    except KeyboardInterrupt:
        app.logger.info('Cancelling service discovery.')
        app.mdns.disable_discovery('_thc_http._tcp')
        app.logger.info('Cancelling service broadcast.')
        app.mdns.unregister('TurretHostController', '_thc_http._tcp', 'local', port)

        app.logger.info('Shutting down.')



if __name__ == '__main__':
    logging.basicConfig()
    run_service(int(sys.argv[1]) if len(sys.argv) > 1 else 1337)