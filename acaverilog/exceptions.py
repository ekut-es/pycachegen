class TargetDirNotEmptyException(Exception):

    def __init__(self, target_dir_path):
        self.target_dir_path = target_dir_path

    def __str__(self):
        return f"Target directory '{self.target_dir_path}' not empty!"


class LatencyIsNotAnInteger(Exception):

    def __init__(self, acadl_object, latency):
        self.acadl_object = acadl_object
        self.latency = latency

    def __str__(self):
        return f"Latency {self.latency} of {type(self.acadl_object)} {self.acadl_object.name} is not an integer!"


class TargetIdEqualOrLessThan0(Exception):

    def __init__(self, forward_port_map):
        self.forward_port_map = forward_port_map

    def __str__(self):
        return f"Forward port map: {self.forward_port_map} contains target id that is equal or less than 0!"
