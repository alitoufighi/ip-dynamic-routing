import select
import sys
import socket
import time
import pickle

LNX_FILES_ROOT = '../tools/'
MAX_TRANSFER_UNIT = 1400


class Address:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)

    def to_tuple(self):
        return self.ip, self.port

    def __repr__(self):
        return f"({self.ip}, {self.port})"


class Interface:
    def __init__(self, ip, port, my_virt_ip, peer_virt_ip):
        self.addr = Address(ip, port)
        self.my_virt_ip = my_virt_ip
        self.peer_virt_ip = peer_virt_ip

    def __repr__(self):
        return f"{self.addr.ip} {self.addr.port} {self.my_virt_ip} {self.peer_virt_ip}"


class Util:
    @staticmethod
    def list_to_interfaces(l):
        """
        :param l: a list of strings in this format: "<ip> <port> <my_virt_ip> <peer_virt_ip>"
        :return: a list of Interface objects
        """
        return [Interface(*line.strip().split()) for line in l]


class IPHeader:

    ROUTING_PROTOCOL = 200
    PRINT_PROTOCOL = 0

    def __init__(self, src_ip, dest_ip, protocol):
        self.version = 4
        # self.type_of_service
        # self.total_length
        # self.id
        # self.fragment_offset
        # self.ttl
        self.protocol = protocol
        # self.checksum
        self.src_addr = src_ip
        self.dst_addr = dest_ip

    def set_protocol(self, protocol):
        self.protocol = protocol


class IPPacket:
    def __init__(self, src_ip, dest_ip, protocol_num, payload):
        self.header = IPHeader(src_ip, dest_ip, protocol_num)
        self.payload = payload


class Node:
    def __init__(self, name):
        self.name = name
        self.addr, self.interfaces = self._read_links()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.addr.to_tuple())
        print(self.addr)
        print(self.interfaces)

        # self.socket.close()

    def _read_links(self):
        with open(f'{LNX_FILES_ROOT}{self.name}.lnx') as f:
            my_status = f.readline().split()
            my_addr = Address(ip=my_status[0], port=my_status[1])
            return my_addr, Util.list_to_interfaces(f.readlines())
        
    def run(self):
        while True:
            input_ready, _, _ = select.select([self.socket, sys.stdin], [], [])
            for sender in input_ready:
                if sender == sys.stdin:
                    self.process_user_input()
                elif sender == self.socket:
                    print("New thing from socket is here")
                    self.process_socket_reply()
            time.sleep(0.3)

    def process_user_input(self):
        try:
            cmd, *args = input().split()
        except ValueError:
            print("Please enter a command.")
            return
        self.cmd_handler(cmd, args)

    def _quit_handler(self):
        print("Exiting...")
        self.socket.close()
        exit(0)

    def _interfaces_handler(self):
        print(f"showing interfaces for {self.addr}")

    def _routes_handler(self):
        pass

    def _down_handler(self, *args):
        try:
            interface_id = args[0]
        except IndexError:
            print("Bad input")
            return
        print(f"Bringing {interface_id} down")

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

    def process_socket_reply(self):
        packet_data, _ = self.socket.recvfrom(MAX_TRANSFER_UNIT)
        ip_packet = pickle.loads(packet_data)
        print(f'Received a new packet from {ip_packet.header.src_addr} with payload "{ip_packet.payload}"')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Run as follows: py main.py <node_name>")
        exit(0)

    node_name = sys.argv[1]
    node = Node(node_name)

    node.run()
