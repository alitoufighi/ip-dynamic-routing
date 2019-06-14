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
        self.table.clear()

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

    def __delitem__(self, key):
        del self.table[key]

    def __str__(self):
        retval = "NO.\tDESTINATION\t\tDISTANCE\tFORWARDING INTERFACE\n"
        retval += "\n".join([f"{index + 1}\t{node}\t\t{routing_table_item.distance}"
                             f"\t\t{routing_table_item.forwarding_interface}"
                             for index, (node, routing_table_item) in enumerate(self.table.items())])
        return retval
