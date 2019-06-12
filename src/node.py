import select
import sys
import socket
import time
import pickle
from address import Address
from ip import IPPacket
from protocol_handler import *
from util import Util
from routing_table_item import *

LNX_FILES_ROOT = '../tools/'
MAX_TRANSMISSION_UNIT = 1400


class Node:
    def __init__(self, name):
        self.name = name
        self.addr, self.interfaces = self._read_links()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.addr.to_tuple())

        self.routing_table = {}
        self.bring_up()

        self.protocol_switcher = {}

        print(f"Node {self.name} started.")
        print(self.addr)
        print(self.interfaces)
        print("---------------------")

    def _broadcast_routing_table_to_neighbors(self, protocol):
        print("BROADCASTING MY ROUTING TABLE TO MY NEIGHBORS")
        print(self.routing_table)
        for interface in self.interfaces:
            if interface.is_up:
                print(f"SENT TO {interface.peer_virt_ip}")
                ip_packet = IPPacket(interface.my_virt_ip,
                                     interface.peer_virt_ip,
                                     protocol,
                                     self.routing_table)
                self.socket.sendto(pickle.dumps(ip_packet),
                                   interface.addr.to_tuple())
        print("--------------------")

    def bring_up(self):
        for interface in self.interfaces:
            if interface.is_up:
                self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                            forwarding_interface=interface.my_virt_ip)
        self._broadcast_routing_table_to_neighbors(ROUTING_TABLE_UPDATE_PROTOCOL)

    def bring_down(self):
        self.routing_table = {}

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
            print(f'{"UP" if interface.is_up else "DOWN"}: \
{interface.addr}, {interface.my_virt_ip} -> {interface.peer_virt_ip}')

    def _routes_handler(self):
        print(f"Routing table for {self.name} is:")
        print(self.routing_table)
        print("---------------------")

    def _down_handler(self, *args):
        try:
            interface_id = args[0]
        except IndexError:
            print("Bad input")
            return

        print(f"Bringing {interface_id} down")
        self.routing_table = {}

        interface = self._find_interface(src_ip=interface_id)
        interface.down()

        for interface in self.interfaces:
            if interface.is_up:
                self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                            forwarding_interface=interface.my_virt_ip)
        self._broadcast_routing_table_to_neighbors(DOWN_PROTOCOL)

    def down_update_handler(self, ip_packet):
        self.routing_table = {}
        for interface in self.interfaces:
            if interface.is_up:
                self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                            forwarding_interface=interface.my_virt_ip)
        self._update_routing_table(ip_packet)

    def _up_handler(self, *args):
        try:
            interface_id = args[0]
        except IndexError:
            print("Bad input")
            return

        self.routing_table = {}

        interface = self._find_interface(src_ip=interface_id)
        interface.up()

        for interface in self.interfaces:
            if interface.is_up:
                self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                            forwarding_interface=interface.my_virt_ip)
        self._broadcast_routing_table_to_neighbors(DOWN_PROTOCOL)

    def _find_interface(self, dest_ip=None, src_ip=None):
        for interface in self.interfaces:
            if dest_ip is not None and interface.peer_virt_ip == dest_ip:
                return interface
            if src_ip is not None and interface.my_virt_ip == src_ip:
                return interface

    def _send_handler(self, *args):
        try:
            virtual_ip, protocol_num, *payload = args
            payload = " ".join(payload)
        except ValueError:
            print("Bad input")
            return

        if self._is_my_packet(virtual_ip):
            print("My Packet Received:")
            print(payload)
            return

        interface = self._find_route(virtual_ip)
        if interface is None:
            print(f"-{virtual_ip}-")
            print(self.routing_table)
            print("No route to host")
            return

        ip_packet = IPPacket(interface.my_virt_ip,
                             virtual_ip,
                             protocol_num,
                             payload)

        self.socket.sendto(pickle.dumps(ip_packet),
                           interface.addr.to_tuple())

        print(f'Sent "{payload}" to {virtual_ip} with proto num {protocol_num}')

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
            "traceroute": self._traceroute_handler,
        }
        return switcher.get(cmd, self._default_cmd)(*args)

    def _traceroute_handler(self, virtual_ip):
        print("‫‪Traceroute‬‬ ‫‪from‬‬ " + self.addr.ip + "to" + virtual_ip)
        path = [self._find_route(virtual_ip).my_virt_ip]
        ip_packet = IPPacket(self._find_route(virtual_ip).my_virt_ip, virtual_ip, TRACEROUTE_PROTOCOL, path)
        self.socket.sendto(pickle.dumps(ip_packet),
                           self._find_route(virtual_ip).addr.to_tuple())

    def rcv_traceroute_handler(self, ip_packet):
        ip_packet.payload.append(self._find_route(ip_packet.header.dst_addr).my_virt_ip)
        if self._is_my_packet(ip_packet.header.dst_addr):
            print("my packet arrived")
            newpacket = IPPacket(ip_packet.header.dst_addr, ip_packet.header.src_addr, TRACEROUTE_PROTOCOL_RESULT,
                                 ip_packet.payload)
            self.socket.sendto(pickle.dumps(newpacket),
                               self._find_route(newpacket.header.dst_addr).addr.to_tuple())
        else:
            print("in another else")
            self.socket.sendto(pickle.dumps(ip_packet),
                               self._find_route(ip_packet.header.dst_addr).addr.to_tuple())

    def trace_route_result_handler(self, ip_packet):
        if self._is_my_packet(ip_packet.header.dst_addr):
            print(ip_packet.payload)
            print(f"Traceroute finished in {len(ip_packet.payload)} hops")
        else:
            print("in else")
            self.socket.sendto(pickle.dumps(ip_packet),
                               self._find_route(ip_packet.header.dst_addr).addr.to_tuple())

    def _update_routing_table(self, ip_packet):
        neighbor_routing_table = ip_packet.payload
        print("----------------------")
        print("NEIGHBOR ROUTING TABLE:")
        print(neighbor_routing_table)
        print("ROUTING TABLE BEFORE UPDATE:")
        print(self.routing_table)
        print("----------------------")

        interface_to_neighbor = self._find_interface(dest_ip=ip_packet.header.src_addr)
        if interface_to_neighbor is None:
            print('wtf')
            return

        changed = False
        for node, routing_table_item in neighbor_routing_table.items():
            if node in self.routing_table:
                if routing_table_item.distance + 1 < self.routing_table[node].distance:
                    self.routing_table[node] = RoutingTableItem(distance=routing_table_item.distance + 1,
                                                                forwarding_interface=interface_to_neighbor.my_virt_ip)
                    changed = True
            else:
                self.routing_table[node] = RoutingTableItem(distance=routing_table_item.distance + 1,
                                                            forwarding_interface=interface_to_neighbor.my_virt_ip)
                changed = True

        print("ROUTING TABLE AFTER UPDATE:")
        print(self.routing_table)
        print("----------------------")
        if changed:
            self._broadcast_routing_table_to_neighbors(ROUTING_TABLE_UPDATE_PROTOCOL)

    def register_handler(self, protocol_num, handler):
        if protocol_num in self.protocol_switcher:
            print(f"handler for {protocol_num} protocol number already exists.")
            return
        print(f"handler for {protocol_num} registered.")
        self.protocol_switcher[protocol_num] = handler

    def run_handler(self, ip_packet):
        protocol_number = int(ip_packet.header.protocol)
        self.protocol_switcher.get(protocol_number, lambda _: print('handler not registered'))(ip_packet)

    def print_handler(self, ip_packet):
        print("PRINT HANDLER CALLED")
        print(ip_packet.payload)
        print("-------------------------")

    def route_handler(self, ip_packet):
        print(f"ROUTE HANDLER CALLED ON {ip_packet}")
        destination_ip = ip_packet.header.dst_addr
        if self._is_my_packet(destination_ip):
            print("My Packet Received:")
            print(ip_packet.payload)
            return
        interface = self._find_route(destination_ip)
        print(interface)
        print("-------------------------")

        self.socket.sendto(pickle.dumps(ip_packet),
                           interface.addr.to_tuple())

    def routing_table_update_handler(self, ip_packet):
        print(f"ROUTING TABLE UPDATE HANDLER CALLED ON {ip_packet}")
        neighbor_routing_table = ip_packet.payload
        print("----------------------")
        print("NEIGHBOR ROUTING TABLE:")
        print(neighbor_routing_table)
        print("ROUTING TABLE BEFORE UPDATE:")
        print(self.routing_table)
        print("----------------------")

        interface_to_neighbor = self._find_interface(dest_ip=ip_packet.header.src_addr)
        if interface_to_neighbor is None:
            print('wtf')
            return

        changed = False
        for node, routing_table_item in neighbor_routing_table.items():
            if node in self.routing_table:
                if routing_table_item.distance + 1 < self.routing_table[node].distance:
                    changed = True
                    self.routing_table[node] = RoutingTableItem(distance=routing_table_item.distance + 1,
                                                                forwarding_interface=interface_to_neighbor.my_virt_ip)
            else:
                changed = True
                self.routing_table[node] = RoutingTableItem(distance=routing_table_item.distance + 1,
                                                            forwarding_interface=interface_to_neighbor.my_virt_ip)

        print("ROUTING TABLE AFTER UPDATE:")
        print(self.routing_table)
        print("----------------------")
        if changed:
            self._broadcast_routing_table_to_neighbors(ROUTING_TABLE_UPDATE_PROTOCOL)

    def process_user_input(self):
        try:
            cmd, *args = input().split()
        except ValueError:
            print("Please enter a command.")
            return
        self.cmd_handler(cmd, args)

    def process_socket_reply(self):
        packet_data, _ = self.socket.recvfrom(MAX_TRANSMISSION_UNIT)
        ip_packet = pickle.loads(packet_data)
        self.run_handler(ip_packet)
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

    def _find_route(self, virtual_ip):
        for interface in self.interfaces:
            if interface.my_virt_ip == self.routing_table[virtual_ip].forwarding_interface:
                return interface

    def _is_my_packet(self, destination_ip):
        for interface in self.interfaces:
            if interface.my_virt_ip == destination_ip:
                return True
        return False
