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
