import os

from jinja2 import Template


def test_func():

    dir_path = os.path.dirname(os.path.realpath(__file__))
    template_path = dir_path + "/verilog_templates/pipeline_stage/PipelineStage.v"
    with open(template_path) as f:
        t = Template(f.read())

    print(t.render(instruction_size=32))
