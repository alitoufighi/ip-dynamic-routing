import select
import sys
import socket
import time
import pickle
from address import Address
from ip import IPPacket
from protocols import *
from util import Util
from routing_table import *

LNX_FILES_ROOT = '../tools/'
MAX_TRANSMISSION_UNIT = 1400


class Node:
    def __init__(self, name):
        self.name = name
        self.addr, self.interfaces = self._read_links()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.addr.to_tuple())

        self.routing_table = RoutingTable()
        self.bring_up()
        self.protocol_switcher = {}
        self.down_interfaces_list = []
        

        print(f"Node {self.name} started.")
        print(self.addr)
        print(self.interfaces)
        print("---------------------")

    @property
    def up_interfaces(self):
        return [interface for interface in self.interfaces if interface.is_up]

    def _broadcast_routing_table_to_neighbors(self, protocol):
        print("BROADCASTING MY ROUTING TABLE TO MY NEIGHBORS")
        print(self.routing_table)
        for interface in self.up_interfaces:
            ip_packet = IPPacket(src_ip=interface.my_virt_ip,
                                 dest_ip=interface.peer_virt_ip,
                                 protocol_num=protocol,
                                 payload=pickle.dumps(self.routing_table))
            self.socket.sendto(pickle.dumps(ip_packet),
                               interface.addr.to_tuple())

    def bring_up(self):
        for interface in self.up_interfaces:
            self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                        forwarding_interface=interface.my_virt_ip)
        self._broadcast_routing_table_to_neighbors(ROUTING_TABLE_UPDATE_PROTOCOL)

    def _read_links(self):
        with open(f'{LNX_FILES_ROOT}{self.name}.lnx') as f:
            my_status = f.readline().split()
            try:
                my_addr = Address(ip=my_status[0], port=my_status[1])
                return my_addr, Util.list_to_interfaces(f.readlines())
            except IndexError:
                print("Malformed lnx file!")
                exit(0)

    def _bring_all_interfaces_down(self):
        for interface in self.up_interfaces:
            self.down_interfaces_list.append(interface.my_virt_ip)
            self.down_interfaces_list.append(interface.peer_virt_ip)

        self.routing_table.clear()

        self._broadcast_change_interface_to_neighbors(changed_interface_addresses=self.down_interfaces_list,
                                                      protocol=DOWN_PROTOCOL)

        for interface in self.up_interfaces:
            interface.down()
            
    def _quit_handler(self):
        print("Exiting...")
        self._bring_all_interfaces_down()
        self.socket.close()
        exit(0)

    def _interfaces_handler(self):
        print(f"Showing interfaces for {self.addr}")
        for interface in self.interfaces:
            print(f'{"UP" if interface.is_up else "DOWN"}:\t'
                  f'{interface.addr}, {interface.my_virt_ip} -> {interface.peer_virt_ip}')

    def _routes_handler(self):
        print(f"Routing table for {self.name} is:")
        print(self.routing_table)
        print("---------------------")

    def _broadcast_change_interface_to_neighbors(self, changed_interface_addresses, protocol):
        payload = {
            'routing_table': pickle.dumps(self.routing_table),
            'interfaces': changed_interface_addresses,
        }
        for interface in self.up_interfaces:
            ip_packet = IPPacket(src_ip=interface.my_virt_ip,
                                 dest_ip=interface.peer_virt_ip,
                                 protocol_num=protocol,
                                 payload=payload)
            self.socket.sendto(pickle.dumps(ip_packet),
                               interface.addr.to_tuple())

    def _down_handler(self, *args):
        try:
            interface_id = args[0]
        except IndexError:
            print("Bad input")
            return
        interface = self._find_interface(src_ip=interface_id)
        self.bring_interface_down(interface)
        print(f"{interface_id} is down.")

    def bring_interface_down(self, down_interface):
        self.down_interfaces_list.append(down_interface.my_virt_ip)
        self.down_interfaces_list.append(down_interface.peer_virt_ip)
        self.routing_table.clear()
        for interface in self.up_interfaces:
            if interface == down_interface:
                continue
            self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                        forwarding_interface=interface.my_virt_ip)
        down_interface_addresses = [down_interface.my_virt_ip, down_interface.peer_virt_ip]
        self._broadcast_change_interface_to_neighbors(changed_interface_addresses=down_interface_addresses,
                                                      protocol=DOWN_PROTOCOL)
        down_interface.down()

    def _is_neighbor_interface_down(self, neighbor_routing_table, source_ip):
        for node, routing_table_item in neighbor_routing_table.items():
            if routing_table_item.distance == 0 and node == source_ip:
                return False
        return True

    def down_update_handler(self, ip_packet):
        neighbor_routing_table = pickle.loads(ip_packet.payload['routing_table'])

        interface_to_neighbor = self._find_interface(dest_ip=ip_packet.header.src_addr)
        if self._is_neighbor_interface_down(neighbor_routing_table, ip_packet.header.src_addr):
            interface_to_neighbor.down()

        down_interface_addresses = ip_packet.payload['interfaces']

        #checked_before = all(address in self.down_interfaces_list for address in down_interface_addresses)
        should_check = False

        for address in down_interface_addresses:
            if address in self.down_interfaces_list:
                continue
            else:
                should_check = True

        if should_check:
            
            for interface_address in down_interface_addresses:
                self.down_interfaces_list.append(interface_address)

            self.routing_table.clear()
            for interface in self.up_interfaces:
                self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                            forwarding_interface=interface.my_virt_ip)

            changed = self._update_routing_table(neighbor_routing_table, interface_to_neighbor)
            if changed:
                self._broadcast_change_interface_to_neighbors(changed_interface_addresses=down_interface_addresses,
                                                              protocol=DOWN_PROTOCOL)
        else:
            changed = self._update_routing_table(neighbor_routing_table, interface_to_neighbor)
            if changed:
                self._broadcast_routing_table_to_neighbors(ROUTING_TABLE_UPDATE_PROTOCOL)

    def up_update_handler(self, ip_packet):
        
        interface_to_neighbor = self._find_interface(dest_ip=ip_packet.header.src_addr)
        interface_to_neighbor.up()  # TODO:detect the interface which its neighbor turned it up and only turn it up!
        self.routing_table.clear()
        self.down_interfaces_list.clear()

        for interface in self.up_interfaces:
            self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                        forwarding_interface=interface.my_virt_ip)

        changed_interface_addresses = ip_packet.payload['interfaces']
        for changed_interface in changed_interface_addresses:
            if changed_interface in self.down_interfaces_list:
                self.down_interfaces_list.remove(changed_interface)

        neighbor_routing_table = pickle.loads(ip_packet.payload['routing_table'])
        changed = self._update_routing_table(neighbor_routing_table, interface_to_neighbor)
        if changed:
            self._broadcast_routing_table_to_neighbors(ROUTING_TABLE_UPDATE_PROTOCOL)

    def _up_handler(self, *args):
        try:
            interface_id = args[0]
        except IndexError:
            print("Bad input")
            return

        
        self.routing_table.clear()  # TODO: test
        self.down_interfaces_list.clear()
        interface = self._find_interface(src_ip=interface_id)
        interface.up()
        changed_interface_addresses = [interface.my_virt_ip, interface.peer_virt_ip]
        for interface in self.up_interfaces:
            self.routing_table[interface.my_virt_ip] = RoutingTableItem(distance=0,
                                                                        forwarding_interface=interface.my_virt_ip)

        self._broadcast_change_interface_to_neighbors(changed_interface_addresses=changed_interface_addresses,
                                                      protocol=UP_PROTOCOL)

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
            print(f"No route to {virtual_ip}")
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
        next_interface = self._find_route(virtual_ip)
        print(f"‫‪Traceroute‬‬ to {virtual_ip}")
        path = [next_interface.my_virt_ip]
        ip_packet = IPPacket(next_interface.my_virt_ip, virtual_ip, TRACEROUTE_PROTOCOL, path)
        self.socket.sendto(pickle.dumps(ip_packet),
                           next_interface.addr.to_tuple())

    def rcv_traceroute_handler(self, ip_packet):
        ip_packet.payload.append(self._find_route(ip_packet.header.dst_addr).my_virt_ip)
        if self._is_my_packet(ip_packet.header.dst_addr):
            newpacket = IPPacket(src_ip=ip_packet.header.dst_addr,
                                 dest_ip=ip_packet.header.src_addr,
                                 protocol_num=TRACEROUTE_PROTOCOL_RESULT,
                                 payload=ip_packet.payload)
            self.socket.sendto(pickle.dumps(newpacket),
                               self._find_route(newpacket.header.dst_addr).addr.to_tuple())
        else:
            self.socket.sendto(pickle.dumps(ip_packet),
                               self._find_route(ip_packet.header.dst_addr).addr.to_tuple())

    def traceroute_result_handler(self, ip_packet):
        if self._is_my_packet(ip_packet.header.dst_addr):
            path = ip_packet.payload
            print("\n".join([f"{index + 1} {item}" for index, item in enumerate(path)]))
            print(f"Traceroute finished in {len(ip_packet.payload)} hops")
        else:
            self.socket.sendto(pickle.dumps(ip_packet),
                               self._find_route(ip_packet.header.dst_addr).addr.to_tuple())

    def _update_routing_table(self, neighbor_routing_table, interface_to_neighbor):

        if not interface_to_neighbor.is_up:
            return True

        if interface_to_neighbor is None or not interface_to_neighbor.is_up:
            print("@@@@@@@@@@@@@@@@@@@ interface to neighbor has issues")
            print(interface_to_neighbor)
            return False

        print("----------------------")
        print("NEIGHBOR ROUTING TABLE:")
        print(neighbor_routing_table)
        print("ROUTING TABLE BEFORE UPDATE:")
        print(self.routing_table)
        print("----------------------")
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
       

        return changed

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
        self.down_interfaces_list.clear()
        interface_to_neighbor = self._find_interface(dest_ip=ip_packet.header.src_addr)
        neighbor_routing_table = pickle.loads(ip_packet.payload)
        changed = self._update_routing_table(neighbor_routing_table, interface_to_neighbor)
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
