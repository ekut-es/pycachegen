from acadl import ACADLObject
from .acadl_object_verilog_template import ACADLObjectVerilogTemplate, LatencyIsNotAnInteger, TargetDirNotEmptyException
from .utils import read_write_template


class ScoreboardVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(self, max_instructions: int, max_source_registers: int,
                 max_target_registers: int) -> None:
        scoreboard = ACADLObject(name="scoreboard")
        super().__init__(scoreboard)

        self.max_instructions = max_instructions
        self.max_source_registers = max_source_registers
        self.max_target_registers = max_target_registers

        self.scoreboard_verilog_file_name = "Scoreboard.v"
        self.tb_file_name = "Scoreboard_tb.cc"

        # TODO checks

        self.scoreboard_template_dir_path = f"{self.verilog_template_dir_path}/scoreboard"
        self.scoreboard_verilog_template_path = f"{self.scoreboard_template_dir_path}/{self.scoreboard_verilog_file_name}"
        self.tb_template_path = f"{self.scoreboard_template_dir_path}/{self.tb_file_name}"

    def generate_verilog(self, target_dir_path: str) -> None:
        # generate scoreboard verilog template
        read_write_template(
            self.scoreboard_verilog_template_path,
            target_dir_path +
            f"/{self.name}_{self.scoreboard_verilog_file_name}",
            name=self.name,
            max_instructions=self.max_instructions,
            max_source_registers=self.max_source_registers,
            max_target_registers=self.max_target_registers)

    def generate_test_bench(self,
                            target_dir_path: str,
                            ignore_target_dir_contents: bool = False) -> None:
        super().generate_test_bench(target_dir_path,
                                    ignore_target_dir_contents)

        self.generate_verilog(target_dir_path)

        # generate SystemC testbench
        read_write_template(self.tb_template_path,
                            target_dir_path +
                            f"/{self.name}_{self.tb_file_name}",
                            name=self.name)

        # generate CMakeLists.txt
        read_write_template(self.scoreboard_template_dir_path +
                            "/CMakeLists.txt",
                            target_dir_path + f"/CMakeLists.txt",
                            name=self.name)
