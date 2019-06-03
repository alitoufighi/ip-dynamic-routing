from node import *

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Run as follows: py main.py <node_name>")
        exit(0)

    node_name = sys.argv[1]
    node = Node(node_name)

    node.register_handler(protocol_num=0, handler=print_handler)
    node.register_handler(protocol_num=200, handler=route_handler)
    node.run()
