from interface import Interface
import sys


class Util:
    @staticmethod
    def list_to_interfaces(l):
        """
        :param l: a list of strings in this format: "<ip> <port> <my_virt_ip> <peer_virt_ip>"
        :return: a list of Interface objects
        """
        return [Interface(*line.strip().split()) for line in l]

    @staticmethod
    def print_last_line_of_output():
        print("---------------------------------")
        print("> ", end="")
        sys.stdout.flush()
