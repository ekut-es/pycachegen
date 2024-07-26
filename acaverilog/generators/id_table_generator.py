from typing import Dict, List
from veriloggen import Module, Case, When

from .module_generator import ModuleGenerator


class IdTableGenerator(ModuleGenerator):

    def __init__(self, name: str, id_length: int,
                 id_table: Dict[int, List[int]]) -> None:
        super().__init__(name, 'IdTable')
        self.id_length = id_length
        self.id_table = id_table

    def generate_module(self) -> Module:

        m = Module(self.base_file_name)

        ID_LENGTH = m.Parameter('ID_LENGTH', self.id_length)
        ID_TABLE_ROWS = m.Parameter('ID_TABLE_ROWS', len(self.id_table))

        id_table = m.Reg("id_table", dims=ID_TABLE_ROWS, width=self.id_length)

        m.Assign(target_id_o(id_table[target_id_i]))

        return m
