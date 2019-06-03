class ProtocolHandler:
    def __init__(self):
        self.switcher = {}

    def register_handler(self, protocol_num, handler):
        if protocol_num in self.switcher:
            print(f"handler for {protocol_num} protocol number already exists.")
            return
        print(f"handler for {protocol_num} registered.")
        self.switcher[protocol_num] = handler

    def run_handler(self, ip_packet):
        protocol_number = int(ip_packet.header.protocol)
        self.switcher.get(protocol_number, lambda _: print('handler not registered'))(ip_packet)


def print_handler(ip_packet):
    print("PRINT HANDLER CALLED")
    print(ip_packet.payload)


def route_handler(ip_packet):
    print(f"ROUTE HANDLER CALLED ON {ip_packet}")
