from .Helpers import get_builtin_type, indent, get_attribute_size, is_flags_enum, get_comments_from_attribute
from .Helpers import get_comments_if_present, create_enum_name, InterfaceType
from .Helpers import get_read_method_name, get_reverse_method_name, get_write_method_name
from .TypescriptGeneratorBase import TypescriptGeneratorBase
from .TypescriptMethodGenerator import TypescriptMethodGenerator


def get_type(attribute):
    return get_builtin_type(attribute['size'])


class TypescriptEnumGenerator(TypescriptGeneratorBase):
    """Typescript enum generator"""

    def __init__(self, name, schema, class_schema):
        super(TypescriptEnumGenerator, self).__init__(name, schema, class_schema)
        self.enum_values = {}
        self.class_type = 'enum'

        if is_flags_enum(name):
            self.implements_list.add(InterfaceType.BitMaskable)

        self._add_enum_values(self.class_schema)

    def _add_private_declaration(self):
        var_type = get_type(self.class_schema)
        self.class_output += [indent(get_comments_if_present('Enum value.'))]
        self.class_output += [indent('private final {0} value;'.format(var_type))] + ['']

    def _add_enum_values(self, enum_attribute):
        enum_attribute_values = enum_attribute['values']
        for current_attribute in enum_attribute_values:
            self.add_enum_value(current_attribute['name'], current_attribute['value'],
                                get_comments_from_attribute(current_attribute, False))

    def _write_enum_values(self):
        enum_type = get_type(self.class_schema)
        enum_length = len(self.enum_values)
        count = 1
        for name, value_comments in self.enum_values.items():
            value, comments = value_comments
            comment_line = get_comments_if_present(comments)
            if comment_line is not None:
                self.class_output += [indent(comment_line)]
            line = '{0} = {1}'.format(name.upper(), value)
            line += ','
            self.class_output += [indent(line)]
            count += 1

    def _add_constructor(self):
        enum_type = get_type(self.class_schema)
        constructor_method = TypescriptMethodGenerator('', '', self.generated_class_name, ['final {0} value'.format(enum_type)])
        constructor_method.add_instructions(['this.value = value'])
        self._add_method_documentation(constructor_method, 'Constructor.', [('value', 'Enum value')], None)
        self._add_method(constructor_method)

    def _add_load_from_binary_custom(self, load_from_binary_method):
        read_data_line = 'stream.{0}()'.format(get_read_method_name(self.class_schema['size']))
        size = get_attribute_size(self.schema, self.class_schema)
        reverse_byte_method = get_reverse_method_name(size).format(read_data_line)
        lines = ['final {0} streamValue = {1}'.format(get_type(self.class_schema), reverse_byte_method)]
        lines += ['return rawValueOf(streamValue)']
        self.wrap_code_in_try(load_from_binary_method, lambda: load_from_binary_method.add_instructions(lines))

    def _add_serialize_custom(self, serialize_method):
        size = get_attribute_size(self.schema, self.class_schema)
        reverse_byte_method = get_reverse_method_name(size).format('this.value')
        serialize_method.add_instructions(['dataOutputStream.{0}({1})'.format(get_write_method_name(size), reverse_byte_method)])

    def add_enum_value(self, name, value, comments):
        self.enum_values[create_enum_name(name)] = [value, comments]

    def _add_public_declarations(self):
        self._add_raw_value_of_method()

    def _add_private_declarations(self):
        self._add_private_declaration()
        self._add_constructor()

    def _calculate_size(self, new_getter):
        new_getter.add_instructions(['return {0}'.format(self.class_schema['size'])])

    def _add_raw_value_of_method(self):
        enum_type = get_type(self.class_schema)
        new_method = TypescriptMethodGenerator('public', self.generated_class_name, 'rawValueOf', ['final {0} value'.format(enum_type)], '', True)
        new_method.add_instructions(['for ({0} current : {0}.values()) {{'.format(self.generated_class_name)], False)
        new_method.add_instructions([indent('if (value == current.value) {')], False)
        new_method.add_instructions([indent('return current', 2)])
        new_method.add_instructions([indent('}')], False)
        new_method.add_instructions(['}'], False)
        new_method.add_instructions(
            ['throw new IllegalArgumentException(value + " was not a backing value for {0}.")'.format(self.generated_class_name)])
        self._add_method_documentation(new_method, 'Gets enum value.', [('value', 'Raw value of the enum')], 'Enum value')
        self._add_method(new_method)

    def _generate_bitmaskable_interface(self):
        new_method = TypescriptMethodGenerator('public', 'long', 'getValue', [], '')
        new_method.add_instructions(['return this.value'])
        self._add_method_documentation(new_method, 'Gets the value of the enum', [], 'Value of the enum.')
        self._add_method(new_method)

    def _generate_interface_methods(self):
        interface_generator = {
            InterfaceType.BitMaskable: self._generate_bitmaskable_interface
        }

        for interfaceType in self.implements_list:
            interface_generator[interfaceType]()

    def generate(self):
        self._add_class_definition()
        self._write_enum_values()
        self.class_output += ['}']
        return self.class_output
