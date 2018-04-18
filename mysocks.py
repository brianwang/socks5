import socks
import simplejson
import SocketServer
import select
import time
import socket
import struct
from SocketServer import *

class SocksLocal(SocketServer.StreamRequestHandler, object):

    def __init__(self, request, client_address, server):
        hosts_str = open('cfg.json', 'r').read()
        hosts_ = simplejson.loads(hosts_str)['hosts']
        ip = hosts_[0]['ip']
        remote_port = hosts_[0]['port']
        username = hosts_[0]['username']
        passwd = hosts_[0]['password']
        self.remote = socks.socksocket()
        self.remote.set_proxy(proxy_type=socks.SOCKS5, addr=ip,
                              port=remote_port, username=username, password=passwd)
        super(SocksLocal, self).__init__(request, client_address, server)

    def setup(self):
        super(SocksLocal, self).setup()

    def finish(self):
        super(SocksLocal, self).finish()
        print 'finished!'
        # self.remote.close()

    def handle(self):
        try:
            print '[%s] socks connection from %s' % (time.ctime(), self.client_address)
            sock = self.connection
            # 1. Version
            sock.recv(262)
            sock.send(b"\x05\x00")
            # 2. Request
            data = self.rfile.read(4)
            mode = ord(data[1])
            addrtype = ord(data[3])
            if addrtype == 1:       # IPv4
                # print "Request for address type is IPv4"
                addr = socket.inet_ntoa(self.rfile.read(4))
            elif addrtype == 3:     # Domain name
                # print "Request for address type is Domain name"
                addr = self.rfile.read(ord(sock.recv(1)[0]))
            port = struct.unpack('>H', self.rfile.read(2))
            reply = b"\x05\x00\x00\x01"
            try:
                # print mode
                if mode == 1:  # 1. Tcp connect
                    self.remote.connect((addr, port[0]))
                    print '[%s] Tcp connect to %s %s' % (time.ctime(), addr, port[0])
                    local = self.remote.getsockname()
                    # print local
                    reply += socket.inet_aton(local[0]) + \
                        struct.pack(">H", local[1])
                else:
                    reply = b"\x05\x07\x00\x01"  # Command not supported
            except socket.error:
                # Connection refused
                print 'error on connect'
                reply = '\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00'
            sock.send(reply)
            # 3. Transfering
            if reply[1] == '\x00':  # Success
                if mode == 1:    # 1. Tcp connect
                    self.handle_tcp(sock, self.remote)
        except socket.error:
            print 'socket error'

    def handle_tcp(self, sock, remote):
        fdset = [sock, remote]
        while True:
            r, w, e = select.select(fdset, [], [])
            if sock in r:
                if remote.send(sock.recv(4096)) <= 0:
                    break
            if remote in r:
                if sock.send(remote.recv(4096)) <= 0:
                    break


PORT = 1112
server = ThreadingTCPServer(('0.0.0.0', PORT), SocksLocal)
print 'start local proxy at port {0}'.format(PORT)
server.serve_forever()


#s.set_proxy(socks.SOCKS5, hosts_['hosts'])
