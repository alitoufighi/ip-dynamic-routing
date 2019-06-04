class RoutingTableItem:
    def __init__(self, distance, forwarding_interface):
        self.distance = distance
        self.forwarding_interface = forwarding_interface

    def __repr__(self):
        return f"Routing Table Item with distance={self.distance} to interface {self.forwarding_interface}"
