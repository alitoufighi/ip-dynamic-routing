from node import *

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Run as follows: py main.py <node_name>")
        exit(0)

    node_name = sys.argv[1]
    node = Node(node_name)

    node.register_handler(protocol_num=PRINT_PROTOCOL, handler=node.print_handler)
    node.register_handler(protocol_num=ROUTE_PROTOCOL, handler=node.route_handler)
    node.register_handler(protocol_num=ROUTING_TABLE_UPDATE_PROTOCOL, handler=node.routing_table_update_handler)
    node.run()
