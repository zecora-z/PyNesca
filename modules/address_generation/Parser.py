import ipaddress
from core.prototypes.AbstractParser import AbstractParser
from core.prototypes.AbstractModuleClass import internal


class Parser(AbstractParser):

    def parse_fields(self, ports:'port_field', ips:'address_field') -> {'ipv4_objects',
    'ports'}:
        result = dict()
        result['ports'] = self.parse_port_field(ports)
        result['ipv4_ranges'] = self.get_all_addresses(ips)
        return result

    @internal
    def parse_port_field(self, ports):
        """
        Parses ports from string, returns them as integers in the list.
        Handles non-existent ports and non-port values.
        """
        if ports:
            # Using set to avoid repetitions
            parsed = set()
            ports = ports.split(",")
            for port in ports:
                try:
                    # Input is in range form ("100-200"):
                    if '-' in port:
                        start, end = map(int, port.split('-'))
                        parsed.update(
                            [p for p in range(start, end + 1) if 65355 >= p > 0])
                    # Input is a single port ("80"):
                    else:
                        parsed.add(int(port))
                except ValueError as e:
                    # If we get any not integer just ignore it
                    pass
            return sorted(list(parsed))
        else:
            # Change to default ports from constant
            return [21, 22, 23, 25, 80, 443, 110, 111, 135, 139, 445, 8080, 8443, 53, 143, 989, 990, 3306, 1080, 5554, 6667, 2222, 4444, 666, 6666, 1337, 2020, 31337]

    @internal
    def parse_address_field(self, ips):
        """
        Parses ip input string, returns the generator over them.

        Supports next inputs:
            1) 1.2.3.4
            2) 192.168.0.0/24
            3) 1.2.3.4 - 5.6.7.8
        Any non-ip value will be ignored.
        """

        # A set to contain non repeating ip objects from ipaddress
        for ip_obj in self.get_all_addresses():
            # The object is just one ip, simply yield it:
            if isinstance(ip_obj, ipaddress.IPv4Address):
                yield ip_obj
            # The object is a network, yield every host in it:
            else:
                for host in ip_obj:
                    yield host

    @internal
    def get_all_addresses(self, ips):
        ip_objects = set()
        inputs = [ip.strip() for ip in ips.split(',')]

        for input_ in inputs:
            try:
                # Input is in range form ("1.2.3.4 - 5.6.7.8"):
                if '-' in input_:
                    input_ips = input_.split('-')
                    ranges = set(
                    ipaddress.summarize_address_range(
                        *map(lambda x: ipaddress.IPv4Address(x.strip()), input_ips)
                        )
                    )
                    ip_objects.update(ranges)
                # Input is in CIDR form ("192.168.0.0/24"):
                elif '/' in input_:
                    network = ipaddress.ip_network(input_)
                    ip_objects.add(network)
                # Input is a single ip ("1.1.1.1"):
                else:
                    ip = ipaddress.ip_address(input_)
                    ip_objects.add(ip)
            except ValueError as e:
                print(e)
                # If we get any non-ip value just ignore it
                pass
            ip_objects = list(ip_objects)
        return ip_objects 
