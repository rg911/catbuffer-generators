import os

from generators.Descriptor import Descriptor
from .Helpers import is_byte_type, is_enum_type, is_struct_type
from .TypescriptClassGenerator import TypescriptClassGenerator
from .TypescriptDefineTypeClassGenerator import TypescriptDefineTypeClassGenerator
from .TypescriptEnumGenerator import TypescriptEnumGenerator
from .TypescriptStaticClassGenerator import TypescriptStaticClassGenerator


class TypescriptFileGenerator:
    """Typescript file generator"""
    enum_class_list = {}

    def __init__(self, schema, options):
        self.current = None
        self.schema = schema
        self.code = []
        self.options = options
        self.imports = []

    def __next__(self):
        self.code = []
        code, name = next(self.current)
        return Descriptor(name + '.ts', code)

    def __iter__(self):
        self.current = self.generate()
        return self

    def update_code(self, generator):
        class_generated = generator.generate()
        for import_type in generator.get_required_import():
            self.code += ['import {0};'.format(import_type)]
        self.code += [''] + class_generated

    def add_copyright(self, copyright_file):
        if os.path.isfile(copyright_file):
            with open(copyright_file) as header:
                self.code = [line.strip() for line in header]

    def set_import(self):
        self.code += ['']

    def _initialize_class(self):
        self.add_copyright(self.options['copyright'])
        self.code = []

    def generate(self):
        for type_descriptor, value in self.schema.items():
            self._initialize_class()
            self.set_import()
            attribute_type = value['type']

            if is_byte_type(attribute_type):
                new_class = TypescriptDefineTypeClassGenerator(type_descriptor, self.schema, value, TypescriptFileGenerator.enum_class_list)
                self.update_code(new_class)
                yield self.code, new_class.get_generated_name()
            elif is_enum_type(attribute_type):
                TypescriptFileGenerator.enum_class_list[type_descriptor] = TypescriptEnumGenerator(type_descriptor, self.schema, value)

            elif is_struct_type(attribute_type):
                if TypescriptClassGenerator.check_should_generate_class(type_descriptor):
                    new_class = TypescriptClassGenerator(type_descriptor, self.schema, value, TypescriptFileGenerator.enum_class_list)
                    self.update_code(new_class)
                    yield self.code, new_class.get_generated_name()

        # write all the enum last just in case there are 'dynamic values'
        for type_descriptor, enum_class in TypescriptFileGenerator.enum_class_list.items():
            self._initialize_class()
            self.set_import()
            self.code += [''] + enum_class.generate()
            yield self.code, enum_class.get_generated_name()

        # write all the  helper files
        helper_files = ['GeneratorUtils']
        for filename in helper_files:
            self._initialize_class()
            new_class = TypescriptStaticClassGenerator(filename)
            self.code += new_class.generate()
            yield self.code, filename
