# pylint: disable=too-few-public-methods
from .Helpers import get_generated_type, AttributeKind, get_attribute_kind, get_comments_from_attribute
from .TypescriptClassGenerator import TypescriptClassGenerator
from .TypescriptMethodGenerator import TypescriptMethodGenerator


class TypescriptDefineTypeClassGenerator(TypescriptClassGenerator):
    """Typescript define type class generator"""

    def __init__(self, name, schema, class_schema, enum_list):
        class_schema['name'] = name[0].lower() + name[1:]
        super(TypescriptDefineTypeClassGenerator, self).__init__(name, schema, class_schema, enum_list)
        self.finalized_class = True

    def _add_public_declarations(self):
        self._add_constructor()
        self._add_getters(self.class_schema, self.schema)

    def _add_private_declarations(self):
        self._add_private_declaration(self.class_schema, self.class_output)
        self.class_output += ['']

    def _add_serialize_custom(self, serialize_method):
        self._generate_serialize_attributes(
            self.class_schema, serialize_method)

    def _add_load_from_binary_custom(self, load_from_binary_method):
        self._generate_load_from_binary_attributes(
            self.class_schema, load_from_binary_method)

    def _calculate_size(self, new_getter):
        new_getter.add_instructions(['return {0}'.format(self.class_schema['size'])])

    def _add_constructor(self):
        attribute_name = self.class_schema['name']
        param_type = get_generated_type(self.schema, self.class_schema)
        new_setter = TypescriptMethodGenerator('', '', 'constructor ', [attribute_name + ': ' + param_type])

        setters = {
            AttributeKind.SIMPLE: self._add_simple_setter,
            AttributeKind.BUFFER: self._add_buffer_setter,
            AttributeKind.ARRAY: self._add_array_setter,
            AttributeKind.CUSTOM: self._add_simple_setter
        }

        attribute_kind = get_attribute_kind(self.class_schema)
        setters[attribute_kind](self.class_schema, new_setter)
        self._add_method_documentation(new_setter, 'Constructor.',
                                       [(attribute_name, get_comments_from_attribute(self.class_schema, False))], None)
        self._add_method(new_setter)
