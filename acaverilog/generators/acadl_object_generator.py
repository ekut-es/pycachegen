from acadl import ACADLObject

from .module_generator import ModuleGenerator


class ACADLObjectGenerator(ModuleGenerator):

    def __init__(self, acadl_object: ACADLObject) -> None:
        self.acadl_object = acadl_object
        super().__init__(self.acadl_object.name,
                         self.acadl_object.__class__.__name__)
