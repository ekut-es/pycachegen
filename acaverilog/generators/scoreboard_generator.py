from math import ceil, log2
from typing import Dict, List
from veriloggen import Module, Submodule, Posedge, Negedge, If, For, AndList, Cond, Systask, Cat

from acadl import FunctionalUnit
from acadl.utils import *

from .module_generator import ModuleGenerator
from ..instruction.instruction_format import InstructionFormat


class ScoreboardGenerator(ModuleGenerator):

    def __init__(self, instruction_format: InstructionFormat,
                 id_table: Dict[int, List[int]],
                 functional_units: List[FunctionalUnit]) -> None:
        super().__init__('sc0', 'Scoreboard')
        self.instruction_format = instruction_format
        self.id_table = id_table
        self.functional_units = functional_units

        self.id_length = instruction_format.id_config.length
        self.max_required_ids = max([len(v) for v in id_table.values()])
        self.id_table_row_length = self.max_required_ids * self.id_length
        self.id_table_rows = len(id_table)
        self.num_units = len(functional_units)
        self.num_units_length = ceil(log2(self.num_units + 1))

    def generate_module(self) -> Module:

        m = Module(self.base_file_name)

        ID_LENGTH = m.Parameter('TARGET_ID_LENGTH', self.id_length)
        MAX_REQUIRED_IDS = m.Parameter('MAX_REQUIRED_IDS',
                                       self.max_required_ids)
        ID_TABLE_ROW_LENGTH = m.Parameter('ID_TABLE_ROW_LENGTH',
                                          self.id_table_row_length)
        ID_TABLE_ROWS = m.Parameter('ID_TABLE_ROWS', self.id_table_rows)
        NUM_UNITS = m.Parameter('NUM_UNITS', self.num_units)

        reset_n_i = m.Input('reset_n_i')

        request_i = []
        for i in range(self.num_units):
            request_i.append(m.Input(f'request_{i}_i', ID_LENGTH))
        request_valid_i = []
        for i in range(self.num_units):
            request_valid_i.append(m.Input(f'request_valid_{i}_i'))
        finished_i = []
        for i in range(self.num_units):
            finished_i.append(m.Input(f'finished_{i}_i', ID_LENGTH))
        finished_valid_i = []
        for i in range(self.num_units):
            finished_valid_i.append(m.Input(f'finished_valid_{i}_i'))

        grant_o = []
        for i in range(self.num_units):
            grant_o.append(m.Output(f'grant_{i}_o'))

        id_table = m.Reg('id_table',
                         dims=ID_TABLE_ROWS,
                         width=ID_TABLE_ROW_LENGTH)
        finished_table = m.Reg('finished_table', ID_TABLE_ROWS)

        required_ids_for_inputs = []
        for i in range(self.num_units):
            required_ids = []
            for j in range(self.max_required_ids):
                required_ids.append(m.Reg(f'required_ids_{i}_{j}', ID_LENGTH))
            required_ids_for_inputs.append(required_ids)

        test = m.Integer('test', initval=ID_LENGTH)
        for i in range(self.num_units):
            for j in range(self.max_required_ids):
                m.Assign(required_ids_for_inputs[i][j](
                    id_table[request_i[i]][0:2]))

        grant = m.Reg('grant', NUM_UNITS)
        for i in range(self.num_units):
            m.Assign(grant[i](AndList(
                *[
                    finished_table[required_ids_for_inputs[i][j]] == 1
                    for j in range(self.max_required_ids)
                ],
                request_valid_i[i] == 1,
            )))

        for i in range(self.num_units):
            m.Assign(grant_o[i](grant[i]))

        it = m.Integer('it')

        m.Always(Negedge(reset_n_i))(
            If(reset_n_i == 0)(
                #Systask('readmemb', 'id_table.txt', id_table),
                [
                    id_table[i](Cat(self.id_table[i][j])
                                for j in range(self.id_table[i]))
                    for i in range(self.id_table_rows)
                ],
                finished_table(0)))

        for i in range(self.num_units):
            m.Always(
                Posedge(finished_valid_i[i])(If(finished_valid_i[i] == 1)(
                    finished_table[finished_i[i]](1))))
