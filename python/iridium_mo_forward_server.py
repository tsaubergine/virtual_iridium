#!/usr/bin/env python3

# splits traffic to Hayes Modem emulator and to an Iridium9602 simulator

import asyncore
import socket
from optparse import OptionParser
import sys

class ConditionalForwardClient(asyncore.dispatcher_with_send):

    def __init__(self, server, host, port):
        asyncore.dispatcher_with_send.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.server = server
           
    def handle_read(self):
        data = self.recv(64)
        if data:
           self.server.send(data)


class ConditionalForwardHandler(asyncore.dispatcher_with_send):

    def __init__(self, sock, addr):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.identified_protocol = False
        self.addr = addr
        self.initial_data = ""
        self.buf = b""
        self.hayes_client = ConditionalForwardClient(self, options.hayes_server, int(options.hayes_port))
        self.sbd_client = ConditionalForwardClient(self, options.sbd_server, int(options.sbd_port))
        self.sbd_write = False
        self.sbd_bytes_remaining = 0

    def handle_read(self):
        data = self.recv(256)
        
        print(data.hex())

        if not data:
            return
        elif self.sbd_write:  # not line mode - raw data
            self.sbd_send_bytes(data)
        elif data == b"+++":
            self.hayes_client.send(data)
        else:  # line based Command data
            self.buf += data
            line_list = self.buf.split(b'\r')
            # partial line
            self.buf = line_list[-1]
        
            for line in line_list[:-1]:
                self.line_process(line)

    def handle_close(self):
        print('Connection closed from %s' % repr(self.addr))
        sys.stdout.flush()
        self.close()

    def line_process(self, line):
        line_cr = line + b'\r'
        line_stripped = line.strip()
        
        print(line)
        print(line_stripped)
        
        if line_stripped.upper() in [b'ATE']:
            self.hayes_client.send(line_cr)
            self.sbd_client.send(line_cr)
        else:
            if len(line) >= 6 and line_stripped[2:6].upper() == b"+SBD":
                self.sbd_client.send(line_cr)
                if len(line) >= 8 and line_stripped[2:8].upper() == b"+SBDWB":
                    parts = line.split(b'=')
                    self.sbd_bytes_remaining = int(parts[1]) + 2  # 2 checksum bytes
                    self.sbd_write = True
            else:
                self.hayes_client.send(line_cr)
    
    def sbd_send_bytes(self, bytes_data):
        self.sbd_bytes_remaining -= len(bytes_data)
        self.sbd_client.send(bytes_data)
        print(self.sbd_bytes_remaining)
        if self.sbd_bytes_remaining <= 0:
            self.sbd_write = False

class ConditionalForwardServer(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            print('Incoming connection from %s' % repr(addr))
            sys.stdout.flush()
            try:
                handler = ConditionalForwardHandler(sock, addr)
            except:
                print("Unexpected error:", sys.exc_info()[0])
            
parser = OptionParser()
parser.add_option("-p", "--port", dest="port", action="store", help="bind port", default=4010)
parser.add_option("-a", "--hayes_address", dest="hayes_server", action="store", help="address to connect to Hayes AT emulator", default="127.0.0.1")
parser.add_option("-b", "--hayes_port", dest="hayes_port", action="store", help="port to connect to Hayes AT emulator", default=4001)
parser.add_option("-c", "--sbd_address", dest="sbd_server", action="store", help="address to connect to SBD emulator", default="127.0.0.1")
parser.add_option("-d", "--sbd_port", dest="sbd_port", action="store", help="port to connect to SBD emulator", default=4020)

(options, args) = parser.parse_args()

forward_address = '0.0.0.0'

print("Iridium Port forwarder starting up ...")
print("Listening on port: {}".format(options.port))
print("Connecting for Iridium9602 SBD on {}:{}".format(options.sbd_server, options.sbd_port))
print("Connecting for Hayes (ATDuck) on {}:{}".format(options.hayes_server, options.hayes_port))
sys.stdout.flush()

server = ConditionalForwardServer(forward_address, int(options.port))
asyncore.loop()
