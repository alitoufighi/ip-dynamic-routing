class IPHeader:

    ROUTING_PROTOCOL = 200
    PRINT_PROTOCOL = 0

    def __init__(self, src_ip, dest_ip, protocol):
        self.version = 4
        self.protocol = protocol
        self.src_addr = src_ip
        self.dst_addr = dest_ip

    def set_protocol(self, protocol):
        self.protocol = protocol


class IPPacket:
    def __init__(self, src_ip, dest_ip, protocol_num, payload):
        self.header = IPHeader(src_ip, dest_ip, protocol_num)
        self.payload = payload
