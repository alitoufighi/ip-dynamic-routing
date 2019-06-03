import select
import sys
import socket
import time
import pickle
from address import Address
from ip import IPPacket
from protocol_handler import *
from util import Util

LNX_FILES_ROOT = '../tools/'
MAX_TRANSFER_UNIT = 1400


class Node:
    def __init__(self, name):
        self.name = name
        self.addr, self.interfaces = self._read_links()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.addr.to_tuple())
        self.protocol_handler = ProtocolHandler()

        print(f"Node {self.name} started.")
        print(self.addr)
        print(self.interfaces)
        print("---------------------")

    def register_handler(self, protocol_num, handler):
        self.protocol_handler.register_handler(protocol_num, handler)

    def _read_links(self):
        with open(f'{LNX_FILES_ROOT}{self.name}.lnx') as f:
            my_status = f.readline().split()
            try:
                my_addr = Address(ip=my_status[0], port=my_status[1])
                return my_addr, Util.list_to_interfaces(f.readlines())
            except IndexError:
                print("Malformed lnx file!")
                exit(0)

    def _quit_handler(self):
        print("Exiting...")
        self.socket.close()
        exit(0)

    def _interfaces_handler(self):
        print(f"Showing interfaces for {self.addr}")
        for interface in self.interfaces:
            print(f'{interface.addr}, {interface.my_virt_ip} -> {interface.peer_virt_ip}')

    def _routes_handler(self):
        pass

    # noinspection PyMethodMayBeStatic
    def _down_handler(self, *args):
        try:
            interface_id = args[0]
        except IndexError:
            print("Bad input")
            return
        print(f"Bringing {interface_id} down")

    # noinspection PyMethodMayBeStatic
    def _up_handler(self, *args):
        try:
            interface_id = args[0]
        except IndexError:
            print("Bad input")
            return
        print(f"Bringing {interface_id} up")

    def _find_interface(self, dest_ip):
        for interface in self.interfaces:
            if interface.peer_virt_ip == dest_ip:
                return interface

    def _send_handler(self, *args):
        try:
            virtual_ip, protocol_num, *payload = args
            payload = " ".join(payload)
        except ValueError:
            print("Bad input")
            return

        interface = self._find_interface(virtual_ip)
        if interface is None:
            print("No route to host")
            return
        ip_packet = IPPacket(interface.my_virt_ip, interface.peer_virt_ip, protocol_num, payload)
        self.socket.sendto(pickle.dumps(ip_packet), interface.addr.to_tuple())
        print(f'Sent "{payload}" to {virtual_ip} with proto num {protocol_num}')

    # noinspection PyMethodMayBeStatic
    def _default_cmd(self):
        print("Invalid command.")

    def cmd_handler(self, cmd, args):
        switcher = {
            "interfaces": self._interfaces_handler,
            "q": self._quit_handler,
            "routes": self._routes_handler,
            "down": self._down_handler,
            "up": self._up_handler,
            "send": self._send_handler,
        }
        return switcher.get(cmd, self._default_cmd)(*args)

    def process_user_input(self):
        try:
            cmd, *args = input().split()
        except ValueError:
            print("Please enter a command.")
            return
        self.cmd_handler(cmd, args)

    def process_socket_reply(self):
        packet_data, _ = self.socket.recvfrom(MAX_TRANSFER_UNIT)
        ip_packet = pickle.loads(packet_data)
        self.protocol_handler.run_handler(ip_packet)
        print(f'Received a new packet from {ip_packet.header.src_addr} with payload "{ip_packet.payload}"')

    def run(self):
        while True:
            input_ready, _, _ = select.select([self.socket, sys.stdin], [], [])
            for sender in input_ready:
                if sender == sys.stdin:
                    self.process_user_input()
                elif sender == self.socket:
                    self.process_socket_reply()
            time.sleep(0.1)
