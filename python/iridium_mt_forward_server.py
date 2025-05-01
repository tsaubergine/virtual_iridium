#!/usr/bin/env python3

# Handles incoming Iridium SBD traffic and port forwards as appropriate based on IMEI 
# Used to allow you to run multiple Iridium9602 simulator instances that can be handled
# by a single MT DirectIP server

import asyncore
import socket
from virtual_iridium.sbd_packets import parse_mt_directip_packet
from collections import deque
import struct
import argparse
import sys

class ConditionalSBDForwardClient(asyncore.dispatcher_with_send):

    def __init__(self, server, host, port):
        asyncore.dispatcher_with_send.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.server = server
           
    def handle_read(self):
        data = self.recv(64)
        if data:
            self.server.send(data)

class ConditionalSBDForwardHandler(asyncore.dispatcher_with_send):

    def __init__(self, sock, addr):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.client = None
        self.addr = addr
        self.data = b''
        self.preheader_fmt = '!bH'
        self.preheader_size = struct.calcsize(self.preheader_fmt)

    def handle_read(self):
        if len(self.data) < self.preheader_size:
            self.data += self.recv(self.preheader_size)
            if not self.data:
                return
            preheader = struct.unpack(self.preheader_fmt, self.data[:self.preheader_size])
            self.msg_length = preheader[1]
        else:
            self.data += self.recv(self.msg_length)

        print(self.msg_length)
        print(self.data.hex())

        if len(self.data) >= self.preheader_size + self.msg_length:
            mt_packet = None
            mt_messages = deque()
            try:
                mt_packet = parse_mt_directip_packet(self.data, mt_messages)
            except:
                print('MT Handler: Invalid message')
                sys.stdout.flush()

            imei = mt_packet[0][1]

            print('Attempting to forward message for imei: {}'.format(imei))

            if imei in forward_address:
                host, port = forward_address[imei]
                print('Forwarding to: {}:{}'.format(host, port))
                self.client = ConditionalSBDForwardClient(self, host, port)
                self.client.send(self.data)
                self.data = b''
            else:
                print('No forwarding set up for imei: {}'.format(imei))
                self.close()

    def handle_close(self):
        print('Connection closed from {}'.format(repr(self.addr)))
        sys.stdout.flush()
        if self.client is not None:
            self.client.close()
        self.close()

class ConditionalSBDForwardServer(asyncore.dispatcher):

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
            print('Incoming connection from {}'.format(repr(addr)))
            sys.stdout.flush()
            try:
                handler = ConditionalSBDForwardHandler(sock, addr)
            except:
                print("Unexpected error:", sys.exc_info()[0])


def parse_forward_argument(forward_arg):
    try:
        imei, ip, port = forward_arg.split(":")
        return imei.encode(), (ip, int(port))
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid format for --forward: {forward_arg}. Expected format: IMEI:IP:PORT")
    
    
parser = argparse.ArgumentParser(description='Iridium MT Forward Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-f", "--forward", help="Tuple of (IMEI:IP Address:Port) of Iridium9602 simulator", action="append", type=parse_forward_argument)
parser.add_argument("-b", "--bind_port", help="Port to bind (mimics 10800 in directip.sbd.iridium.com)", default=40002, type=int)
args = parser.parse_args()

# this script listens (binds) on this port
mt_sbd_address = '0.0.0.0'
mt_sbd_port = args.bind_port

# maps imei to address and port                    
forward_address = dict(args.forward or [])

print(f"Forwarding to: {forward_address}")

print("Iridium SBD MT Port forwarder starting up ...")
print("Listening for SBD on port: {}".format(mt_sbd_port))
sys.stdout.flush()

sbd_server = ConditionalSBDForwardServer(mt_sbd_address, mt_sbd_port)
asyncore.loop()
