from .acadl_object_verilog_template import ACADLObjectVerilogTemplate
from .instruction_memory_verilog_template import InstructionMemoryVerilogTemplate
from acadl import InstructionFetchStage

from jinja2 import Template


class InstructionFetchStageVerilogTemplate(ACADLObjectVerilogTemplate):

    def __init__(
        self, instruction_fetch_stage: InstructionFetchStage,
        instruction_memory_verilog_template: InstructionMemoryVerilogTemplate
    ) -> None:
        super().__init__(instruction_fetch_stage)

        self.instruction_fetch_stage_verilog_file_name = "InstructionFetchStage.v"
        self.tb_file_name = "InstructionFetchStage_tb.cc"

        self.instruction_memory_verilog_template = instruction_memory_verilog_template

        # TODO checks

        self.instruction_fetch_stage_template_dir_path = f"{self.verilog_template_dir_path}/instruction_fetch_stage"
        self.instruction_fetch_stage_verilog_template_path = f"{self.instruction_fetch_stage_template_dir_path}/{self.instruction_fetch_stage_verilog_file_name}"

    def generate_verilog(self, target_dir_path: str) -> None:
        # generate instruction fetch stage verilog
        with open(self.instruction_fetch_stage_verilog_template_path) as f:
            instruction_fetch_stage_verilog_template = Template(f.read())

        with open(
                target_dir_path +
                f"/{self.name}_{self.instruction_fetch_stage_verilog_file_name}",
                "w+") as f:
            f.write(
                instruction_fetch_stage_verilog_template.render(
                    name=self.name,
                    data_width=self.instruction_memory_verilog_template.
                    acadl_object.data_width,
                    max_data_word_distance=self.
                    instruction_memory_verilog_template.max_data_word_distance,
                    port_width=self.instruction_memory_verilog_template.
                    acadl_object.port_width,
                    address_width=self.instruction_memory_verilog_template.
                    address_width))
