class RoutingTableItem:
    def __init__(self, distance, forwarding_interface):
        self.distance = distance
        self.forwarding_interface = forwarding_interface

    def __repr__(self):
        return f"with distance={self.distance} using interface {self.forwarding_interface}"


class RoutingTable:
    def __init__(self):
        self.table = {}

    def clear(self):
        self.table = {}

    def items(self):
        return self.table.items()

    def get(self):
        return self.table

    def __getitem__(self, key):
        return self.table[key]

    def __iter__(self):
        return iter(self.table)

    def __setitem__(self, key, value):
        self.table[key] = value

    def __str__(self):
        return "\n".join([f"{node}: {routing_table_item}" for node, routing_table_item in self.table.items()])
