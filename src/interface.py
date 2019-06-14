from address import Address


class Interface:
    def __init__(self, ip, port, my_virt_ip, peer_virt_ip):
        self.addr = Address(ip, port)
        self.my_virt_ip = my_virt_ip
        self.peer_virt_ip = peer_virt_ip
        self.is_up = False

    def up(self):
        self.is_up = True

    def down(self):
        self.is_up = False

    def __repr__(self):
        return f"{self.addr.ip} {self.addr.port} {self.my_virt_ip} {self.peer_virt_ip}"
