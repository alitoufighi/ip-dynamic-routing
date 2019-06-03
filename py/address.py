class Address:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)

    def to_tuple(self):
        return self.ip, self.port

    def __repr__(self):
        return f"({self.ip}, {self.port})"
