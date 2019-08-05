from .Helpers import create_enum_name, get_default_value, get_class_type_from_name, get_comment_from_name
from .Helpers import get_attribute_kind, TypeDescriptorDisposition, get_attribute_if_size, get_byte_convert_method_name
from .Helpers import get_generated_class_name, get_builtin_type, indent, get_attribute_size
from .Helpers import get_generated_type, get_attribute_property_equal, AttributeKind, is_byte_type
from .Helpers import get_read_method_name, get_reverse_method_name, get_write_method_name, is_enum_type
from .Helpers import is_builtin_type, get_comments_from_attribute, get_import_for_type, format_import, TypeDescriptorType
from .TypescriptGeneratorBase import TypescriptGeneratorBase
from .TypescriptMethodGenerator import TypescriptMethodGenerator

def capitalize_first_character(string):
    return string[0].upper() + string[1:]


class TypescriptClassGenerator(TypescriptGeneratorBase):
    """Typescript class generator"""

    def __init__(self, name, schema, class_schema, enum_list):
        super(TypescriptClassGenerator, self).__init__(name, schema, class_schema)
        self.enum_list = enum_list
        self.class_type = 'class'
        self.condition_list = []
        self.import_list = []
        self.load_from_binary_atrribute_list = []
        self._add_required_import(format_import('GeneratorUtils'))

        if 'layout' in self.class_schema:
            # Find base class
            self._foreach_attributes(
                self.class_schema['layout'], self._find_base_callback)
            # Find any condition variables
            self._recurse_foreach_attribute(
                self.name, self._create_condition_list, self.condition_list, [])

    @staticmethod
    def _is_inline_class(attribute):
        return 'disposition' in attribute and attribute['disposition'] == TypeDescriptorDisposition.Inline.value

    def _find_base_callback(self, attribute):
        if self._is_inline_class(attribute) and self.should_generate_class(attribute['type']):
            self.base_class_name = attribute['type']
            self.finalized_class = True
            self.import_list.append(self.base_class_name)
            return True
        return False

    @staticmethod
    def _is_conditional_attribute(attribute):
        return 'condition' in attribute

    def _create_condition_list(self, attribute, condition_list):
        if self._is_conditional_attribute(attribute):
            condition_list.append(attribute)

    def _should_declaration(self, attribute):
        return not self.is_count_size_field(attribute) and attribute['name'] != 'size'

    def _get_body_class_name(self):
        body_name = self.name if not self.name.startswith('Embedded') else self.name[8:]
        return '{0}Body'.format(body_name)

    def _add_private_declarations(self):
        self._recurse_foreach_attribute(self.name, self._add_private_declaration, self.class_output,
                                        [self.base_class_name, self._get_body_class_name()])
        self.class_output += ['']

    def _add_required_import_if_needed(self, var_type):
        import_string = None
        if import_string:
            self._add_required_import(import_string)

    def _add_private_declaration(self, attribute, private_output):
        if not self.is_count_size_field(attribute):
            line = get_comments_from_attribute(attribute)
            if line is not None:
                private_output += [indent(line)]
            attribute_name = attribute['name']
            var_type = get_generated_type(self.schema, attribute)
            self._add_required_import_if_needed(var_type)
            private_output += [indent('{1}: {0};'.format(var_type, attribute_name))]

    @staticmethod
    def _get_generated_getter_name(attribute_name):
        return 'get{0}'.format(capitalize_first_character(attribute_name))

    @staticmethod
    def _add_simple_getter(attribute, new_getter):
        new_getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    @staticmethod
    def _add_buffer_getter(attribute, new_getter):
        new_getter.add_instructions(
            ['return this.{0}'.format(attribute['name'])])

    # pylint: disable-msg=too-many-arguments
    def _add_if_condition_for_variable_if_needed(self, attribute, writer, object_prefix, if_condition, code_lines, add_semicolon=True):
        condition_type_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'name', attribute['condition'])
        condition_type = '{0}.{1}'.format(get_generated_class_name(condition_type_attribute['type'], condition_type_attribute, self.schema),
                                          create_enum_name(attribute['condition_value']))

        writer.add_instructions(['if ({0}{1} {2} {3}) {{'.format(object_prefix, attribute['condition'], if_condition, condition_type)],
                                False)
        for line in code_lines:
            writer.add_instructions([indent(line)], add_semicolon)
        writer.add_instructions(['}'], False)

    def _add_method_condition(self, attribute, method_writer):
        if 'condition' in attribute:
            code_lines = ['throw new Typescript.lang.IllegalStateException("{0} is not set to {1}.")'.format(
                attribute['condition'], create_enum_name(attribute['condition_value']))]
            self._add_if_condition_for_variable_if_needed(attribute, method_writer, 'this.', '!=', code_lines)

    def _add_getter(self, attribute, schema):
        attribute_name = attribute['name']
        return_type = get_generated_type(schema, attribute)
        self._add_required_import_if_needed(return_type)
        new_getter = TypescriptMethodGenerator('public', return_type, self._get_generated_getter_name(attribute_name), [])

        if 'aggregate_class' in attribute:
            # This is just a pass through
            new_getter.add_instructions(
                ['return this.{0}.{1}()'.format(self._get_name_from_type(attribute['aggregate_class']),
                                                self._get_generated_getter_name(attribute_name))])
        else:
            self._add_method_condition(attribute, new_getter)
            getters = {
                AttributeKind.SIMPLE: self._add_simple_getter,
                AttributeKind.BUFFER: self._add_buffer_getter,
                AttributeKind.ARRAY: self._add_simple_getter,
                AttributeKind.CUSTOM: self._add_simple_getter,
                AttributeKind.FLAGS: self._add_simple_getter
            }
            attribute_kind = get_attribute_kind(attribute)
            getters[attribute_kind](attribute, new_getter)

        # If the comments is empty then just use name in the description
        description = get_comments_from_attribute(attribute, False)
        self._add_method_documentation(new_getter, 'Gets {0}.'.format(description), [], description)
        self._add_method(new_getter)

    @staticmethod
    def _add_simple_setter(attribute, new_setter):
        new_setter.add_instructions(['this.{0} = {0}'.format(attribute['name'])])

    @staticmethod
    def _add_array_setter(attribute, new_setter):
        new_setter.add_instructions(['this.{0} = {0}'.format(attribute['name'])])

    def _add_buffer_setter(self, attribute, new_setter):
        attribute_name = attribute['name']
        new_setter.add_instructions(['this.{0} = {0}'.format(attribute_name)])

    def _add_size_value(self, attribute, method_writer):
        kind = get_attribute_kind(attribute)
        line = 'size += '
        if kind == AttributeKind.SIMPLE:
            line += '{0}; // {1}'.format(attribute['size'], attribute['name'])
        elif kind == AttributeKind.BUFFER:
            line += 'this.{0}.length;'.format(attribute['name'])
        elif kind == AttributeKind.ARRAY:
            line = ''
            line += 'this.{0}.forEach((o) => size += o.getSize());'.format(attribute['name'])
        elif kind == AttributeKind.FLAGS:
            line += '{0}.values()[0].getSize(); // {1}'.format(get_generated_class_name(attribute['type'], attribute, self.schema),
                                                               attribute['name'])
        else:
            line += self._get_custom_attribute_size_getter(attribute)

        self._add_attribute_condition_if_needed(attribute, method_writer, 'this.', [line], False)

    def _get_custom_attribute_size_getter(self, attribute):
        for type_descriptor, value in self.schema.items():
            attribute_type = value['type']
            attribute_name = type_descriptor
            if is_enum_type(attribute_type) and attribute_name == attribute['type']:
                return '{0}; // {1}'.format(value['size'], attribute['name'])
        return 'this.{0}.getSize();'.format(attribute['name'])

    def _calculate_size(self, new_getter):
        return_type = 'number'
        if self.base_class_name is not None:
            new_getter.add_instructions(['let size: {0} = super.getSize()'.format(return_type)])
        else:
            new_getter.add_instructions(['let size: {0} = 0'.format(return_type)])
        self._recurse_foreach_attribute(self.name, self._add_size_value, new_getter, [self.base_class_name, self._get_body_class_name()])
        new_getter.add_instructions(['return size'])

    def _add_stream_size_getter(self):
        new_getter = TypescriptMethodGenerator('protected', 'number', 'getStreamSize', [])
        new_getter.add_instructions(['return this.size'])
        self._add_method_documentation(new_getter, 'Gets the size if created from a stream otherwise zero', [], 'Object size from stream')
        self._add_method(new_getter)

    def _add_getters(self, attribute, schema):
        if self._should_declaration(attribute):
            self._add_getter(attribute, schema)
        elif attribute['name'] == 'size':
            self._add_stream_size_getter()

    @staticmethod
    def _get_name_from_type(type_name):
        return type_name[0].lower() + type_name[1:]

    def _recurse_foreach_attribute(self, class_name, callback, context, ignore_inline_class):
        class_generated = (class_name != self.name and self.should_generate_class(class_name))
        for attribute in self.schema[class_name]['layout']:
            if class_generated:
                attribute['aggregate_class'] = class_name

            if 'disposition' in attribute:
                inline_class = attribute['type']
                if attribute['disposition'] == TypeDescriptorDisposition.Inline.value:
                    if self.should_generate_class(inline_class):
                        # Class was grenerated so it can be declare aggregate
                        attribute['name'] = self._get_name_from_type(inline_class)
                        if (self.base_class_name == inline_class and
                                self.base_class_name in ignore_inline_class):
                            continue  # skip the base class
                        if inline_class in ignore_inline_class:
                            callback(attribute, context)
                            continue

                    self._recurse_foreach_attribute(inline_class, callback, context, ignore_inline_class)
                elif attribute['disposition'] == TypeDescriptorDisposition.Const.value:
                    # add dynamic enum if present in this class
                    enum_name = attribute['type']
                    if enum_name in self.enum_list:
                        self.enum_list[enum_name].add_enum_value(self.generated_class_name, attribute['value'],
                                                                 get_comment_from_name(self.generated_class_name))
                    continue
            else:
                callback(attribute, context)

    def _init_other_attribute_in_condition(self, attribute, obj_prefix, code_lines):
        if 'condition' in attribute:
            for condition_attribute in self.condition_list:
                if attribute['name'] != condition_attribute['name']:
                    code_lines.append('{0}{1} = {2}'.format(obj_prefix, condition_attribute['name'], get_default_value(attribute)))

    def _add_attribute_condition_if_needed(self, attribute, method_writer, obj_prefix, code_lines, add_semicolon=True):
        if 'condition' in attribute:
            self._add_if_condition_for_variable_if_needed(attribute, method_writer, obj_prefix, '==', code_lines, add_semicolon)
        else:
            method_writer.add_instructions(code_lines, add_semicolon)

    def _load_from_binary_simple(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        const_delaration = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(size)
        read_method_name = get_byte_convert_method_name(size).format(const_delaration)
        lines = ['const {0} = {1}'.format(attribute['name'], read_method_name)]
        lines += ['byteArray = byteArray.splice(0, {0})'.format(size)]
        self._init_other_attribute_in_condition(attribute, 'this.', lines)
        self._add_attribute_condition_if_needed(attribute, load_from_binary_method, 'this.', lines)
        if len(self.load_from_binary_atrribute_list) <= 1:
            load_from_binary_method.add_instructions(['return new {0}({1})'.format(self.generated_class_name, attribute['name'])])

    def _load_from_binary_buffer(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        lines = ['const {0} = GeneratorUtils.getBytes(Uint8Array.from(byteArray), {1})'.format(attribute['name'], size)]
        lines += ['byteArray = byteArray.splice(0, {0})'.format(size)]
        load_from_binary_method.add_instructions(lines)
        if len(self.load_from_binary_atrribute_list) <= 1:
            load_from_binary_method.add_instructions(['return new {0}({1})'.format(self.generated_class_name, attribute['name'])])

    def _load_from_binary_array(self, attribute, load_from_binary_method):
        attribute_typename = attribute['type']
        attribute_sizename = attribute['size']
        attribute_name = attribute['name']
        load_from_binary_method.add_instructions(['const {0} = []'.format(attribute_name)])
        load_from_binary_method.add_instructions(['for (let i = 0; i < {0}; i++) {{'.format(attribute_sizename)], False)

        if is_byte_type(attribute_typename):
            const_delaration = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), 1)'
            read_method_name = get_byte_convert_method_name(1).format(const_delaration)
            load_from_binary_method.add_instructions(
                [indent('const item = {0}'.format(read_method_name))])
            load_from_binary_method.add_instructions([indent('{0}.add(stream.{1}())'.format(attribute_name, get_read_method_name(1)))])
        else:
            load_from_binary_method.add_instructions(
                [indent('const item = {0}.loadFromBinary(Uint8Array.from(byteArray))'.format(get_generated_class_name(attribute_typename, attribute,
                                                                                                                      self.schema)))])
        load_from_binary_method.add_instructions([indent('{0}.push(item)'.format(attribute_name))])
        load_from_binary_method.add_instructions([indent('byteArray = byteArray.splice(0, item.getSize())')])
        load_from_binary_method.add_instructions(['}'], False)

    def _load_from_binary_custom(self, attribute, load_from_binary_method):
        is_custom_type_enum = False
        customer_enum_size = 0
        for type_descriptor, value in self.schema.items():
            enum_attribute_type = value['type']
            enum_attribute_name = type_descriptor
            if is_enum_type(enum_attribute_type) and enum_attribute_name == attribute['type']:
                is_custom_type_enum = True
                customer_enum_size = value['size']

        if is_custom_type_enum and customer_enum_size > 0:
            const_declare = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(customer_enum_size)
            enum_method = get_byte_convert_method_name(customer_enum_size).format(const_declare)
            lines = ['const {0} = {1}'.format(attribute['name'], enum_method)]
            lines += ['byteArray = byteArray.splice(0, {0})'.format(customer_enum_size)]
        else:
            lines = ['const {0} = {1}.loadFromBinary(Uint8Array.from(byteArray))'.format(attribute['name'],
                                                                                         get_generated_class_name(attribute['type'],
                                                                                                                  attribute, self.schema))]
            lines += ['byteArray = byteArray.splice(0, {0}.getSize())'.format(attribute['name'])]
        
        self._init_other_attribute_in_condition(attribute, 'this.', lines)
        self._add_attribute_condition_if_needed(attribute, load_from_binary_method, 'this.', lines)

    def _load_from_binary_flags(self, attribute, load_from_binary_method):
        size = get_attribute_size(self.schema, attribute)
        const_declare = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(size)
        read_method_name = get_byte_convert_method_name(size).format(const_declare)
        reverse_byte_method = get_reverse_method_name(size).format(read_method_name)
        lines = ['this.{0} = GeneratorUtils.toSet({1}, {2})'.format(attribute['name'],
                                                                    get_class_type_from_name(
                                                                        get_generated_class_name(attribute['type'], attribute,
                                                                                                 self.schema)),
                                                                    reverse_byte_method)]
        self._init_other_attribute_in_condition(attribute, 'this.', lines)
        self._add_attribute_condition_if_needed(attribute, load_from_binary_method, 'this.', lines)

    @staticmethod
    def is_count_size_field(field):
        return field['name'].endswith('Size') or field['name'].endswith('Count')

    def _generate_load_from_binary_attributes(self, attribute, load_from_binary_method):
        if self.is_count_size_field(attribute):
            const_declare = 'GeneratorUtils.getBytes(Uint8Array.from(byteArray), {0})'.format(attribute['size'])
            size_method = get_byte_convert_method_name(attribute['size']).format(const_declare)
            lines = ['const {0} = {1}'.format(attribute['name'], size_method)]
            lines += ['byteArray = byteArray.splice(0, {0})'.format(attribute['size'])]
            load_from_binary_method.add_instructions(lines)
        else:
            load_attribute = {
                AttributeKind.SIMPLE: self._load_from_binary_simple,
                AttributeKind.BUFFER: self._load_from_binary_buffer,
                AttributeKind.ARRAY: self._load_from_binary_array,
                AttributeKind.CUSTOM: self._load_from_binary_custom,
                AttributeKind.FLAGS: self._load_from_binary_flags
            }

            attribute_kind = get_attribute_kind(attribute)
            load_attribute[attribute_kind](attribute, load_from_binary_method)

    def _serialize_attribute_simple(self, attribute, serialize_method):
        size = get_attribute_size(self.schema, attribute)
        lines = []
        if (size < 8):
            method = '{0}(this.{1}(), {2})'.format(get_read_method_name(size),
                                                   self._get_generated_getter_name(attribute['name']),
                                                   size)
        else:
            method = '{0}(this.{1}())'.format(get_read_method_name(size),
                                              self._get_generated_getter_name(attribute['name']))
        # reverse_method = get_reverse_method_name(size).format('new Uint8Array(this.' +
        #                                                       self._get_generated_getter_name(attribute['name'] + '())'))
        lines.append('const {0}Bytes = GeneratorUtils.fitByteArray({1}, {2});'.format(attribute['name'], method, size))
        lines.append('newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute['name']+'Bytes'))
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines)

    def _serialize_attribute_buffer(self, attribute, serialize_method):
        attribute_size = attribute['size']
        attribute_name = attribute['name']
        method = 'GeneratorUtils.fitByteArray(this.{0}, {1}'.format(attribute_name,
                                                                    'this.' + attribute_name +
                                                                    '.length' if isinstance(attribute_size, str) else attribute_size)
        line = 'newArray = GeneratorUtils.concatTypedArrays(newArray, {0}));'.format(method)
        serialize_method.add_instructions([line], False)

    @staticmethod
    def _get_serialize_name(attribute_name):
        return '{0}Bytes'.format(attribute_name)

    def _serialize_attribute_array(self, attribute, serialize_method):
        attribute_typename = attribute['type']
        attribute_size = attribute['size']
        attribute_name = attribute['name']
        serialize_method.add_instructions(['this.{0}.forEach((item) => {{'.format(attribute_name)], False)

        if is_byte_type(attribute_typename):
            byte_method = 'GeneratorUtils.fitByteArray(this.{0}, {1}'.format(attribute_name, attribute_size)
            byte_line = 'newArray = GeneratorUtils.concatTypedArrays(newArray, {0}));'.format(byte_method)
            serialize_method.add_instructions(
                [indent(byte_line)])
        else:
            attribute_bytes_name = self._get_serialize_name(attribute_name)
            serialize_method.add_instructions(
                [indent('const {0} = GeneratorUtils.fitByteArray(item.serialize(), item.getSize())'.format(attribute_bytes_name))])
            serialize_method.add_instructions(
                [indent('newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute_bytes_name))])
        serialize_method.add_instructions(['})'], True)

    def _serialize_attribute_custom(self, attribute, serialize_method):
        attribute_name = attribute['name']
        attribute_bytes_name = self._get_serialize_name(attribute_name)
        is_custom_type_enum = False
        customer_enum_size = 0
        for type_descriptor, value in self.schema.items():
            enum_attribute_type = value['type']
            enum_attribute_name = type_descriptor
            if is_enum_type(enum_attribute_type) and enum_attribute_name == attribute['type']:
                is_custom_type_enum = True
                customer_enum_size = value['size']
        if is_custom_type_enum and customer_enum_size > 0:
            lines = ['const {0} = GeneratorUtils.fitByteArray(GeneratorUtils.uintToBuffer(this.{1}, {2}), {2})'
                     .format(attribute_bytes_name, attribute_name, customer_enum_size)]
        else:
            lines = ['const {0} = GeneratorUtils.fitByteArray(this.{1}.serialize(), this.{1}.getSize())'.format(attribute_bytes_name,
                                                                                                                attribute_name)]
        lines += ['newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute_bytes_name)]
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines)

    def _serialize_attribute_flags(self, attribute, serialize_method):
        attribute_name = attribute['name']
        size = get_attribute_size(self.schema, attribute)
        enum_type = get_builtin_type(size)
        line = '{0} bitMask = '.format(enum_type)
        if size < 8:  # cast is required since the bitmask is a long
            line += '({0}) '.format(enum_type)
        line += 'GeneratorUtils.toLong({0}, this.{1})'.format(
            get_class_type_from_name(get_generated_class_name(attribute['type'], attribute, self.schema)),
            attribute_name)

        lines = [line]
        reverse_byte_method = get_reverse_method_name(size).format('bitMask')
        lines += ['dataOutputStream.{0}({1})'.format(get_write_method_name(size), reverse_byte_method)]
        self._add_attribute_condition_if_needed(attribute, serialize_method, 'this.', lines)

    def _generate_serialize_attributes(self, attribute, serialize_method):
        attribute_name = attribute['name']
        attribute_bytes_name = self._get_serialize_name(attribute_name)
        if self.is_count_size_field(attribute):
            size = get_attribute_size(self.schema, attribute)
            size_extension = '.length'
            full_property_name = '{0}'.format(get_attribute_if_size(attribute['name'], self.class_schema['layout'],
                                                                    self.schema) + size_extension)
            method = '{0}(this.{1}, {2})'.format(get_read_method_name(size),
                                                 full_property_name,
                                                 size)
            line = 'const {0} = GeneratorUtils.fitByteArray({1}, {2})'.format(attribute_bytes_name, method, size)
            line2 = 'newArray = GeneratorUtils.concatTypedArrays(newArray, {0})'.format(attribute_bytes_name)
            # line = 'dataOutputStream.{0}({1})'.format(get_write_method_name(size), reverse_byte_method)
            serialize_method.add_instructions([line])
            serialize_method.add_instructions([line2])
        else:
            serialize_attribute = {
                AttributeKind.SIMPLE: self._serialize_attribute_simple,
                AttributeKind.BUFFER: self._serialize_attribute_buffer,
                AttributeKind.ARRAY: self._serialize_attribute_array,
                AttributeKind.CUSTOM: self._serialize_attribute_custom,
                AttributeKind.FLAGS: self._serialize_attribute_flags
            }

            attribute_kind = get_attribute_kind(attribute)
            serialize_attribute[attribute_kind](attribute, serialize_method)

    def _add_getters_field(self):
        self._recurse_foreach_attribute(
            self.name, self._add_getters, self.schema, [self.base_class_name])

    def _add_public_declarations(self):
        if self.condition_list:
            self._add_constructors()
            self._add_factory_methods()
        else:
            self._add_constructor()
            if self.base_class_name is None:
                self._add_factory_method()
        self._add_getters_field()

    def _add_load_from_binary_custom(self, load_from_binary_method):
        if self.base_class_name is not None:
            lines = ['const superObject = {0}.loadFromBinary(Uint8Array.from(byteArray))'.format(get_generated_class_name(self.base_class_name, self.schema[self.base_class_name], self.schema))]
            lines += ['byteArray = byteArray.splice(0, superObject.getSize())']
            load_from_binary_method.add_instructions(lines)

        self._recurse_foreach_attribute(self.name, self._generate_load_from_binary_attributes,
                                        load_from_binary_method, [self.base_class_name, self._get_body_class_name()])
        load_from_binary_method.add_instructions(['return new {0}({1})'.format(self.generated_class_name,
                                                                               ', '.join(self.load_from_binary_atrribute_list))])

    def _add_serialize_custom(self, serialize_method):
        if self.base_class_name is not None:
            serialize_method.add_instructions(['const superBytes = GeneratorUtils.fitByteArray(super.serialize(), super.getSize())'])
            serialize_method.add_instructions(['GeneratorUtils.concatTypedArrays(newArray, superBytes)'])
        self._recurse_foreach_attribute(self.name, self._generate_serialize_attributes,
                                        serialize_method, [self.base_class_name, self._get_body_class_name()])

    def _add_to_variable(self, attribute, context):
        param_list, condition_attribute = context
        attribute_name = attribute['name']
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute):
            param_list.append(attribute_name)

    @staticmethod
    def _should_add_base_on_condition(attribute, condition_attribute):
        attribute_name = attribute['name']
        if condition_attribute is not None:
            if 'condition' in attribute:
                if condition_attribute['condition'] == attribute['condition'] and condition_attribute['name'] != attribute_name:
                    return False  # Skip all other conditions attribute
            elif condition_attribute['condition'] == attribute_name:
                return False
        return True

    def _add_to_param(self, attribute, context):
        param_list, condition_attribute = context
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute):
            attribute_name = attribute['name']
            attribute_type = get_generated_type(self.schema, attribute)
            if attribute_type is not 'number' and attribute_type is not 'Uint8Array':
                self._add_required_import(format_import(attribute_type))
            param_list.append('{1}: {0}'.format(attribute_type, attribute_name))

    def _create_list(self, name, callback, condition_attribute):
        param_list = []
        self._recurse_foreach_attribute(name, callback, (param_list, condition_attribute), [])
        param_string = param_list[0]
        for param in param_list[1:]:
            param_string += ', {0}'.format(param)
        return param_string

    def _create_custom_variable_list(self, name, callback, condition_attribute, object_name):
        param_list = []
        self._recurse_foreach_attribute(name, callback, (param_list, condition_attribute), [])
        param_string = object_name + '.' + param_list[0]
        for param in param_list[1:]:
            param_string += ', {0}'.format(object_name + '.' + param)
        return param_string

    def _create_param_list(self, condition_attribute):
        return self._create_list(self.name, self._add_to_param, condition_attribute)

    def _add_name_comment(self, attribute, context):
        comment_list, condition_attribute = context
        if self._should_declaration(attribute) and self._should_add_base_on_condition(attribute, condition_attribute):
            comment_list.append((attribute['name'], get_comments_from_attribute(attribute, False)))

    def _create_name_comment_list(self, name, condition_variable):
        name_comment_list = []
        self._recurse_foreach_attribute(name, self._add_name_comment, (name_comment_list, condition_variable), [])
        return name_comment_list

    def _add_attribute_to_list(self, attribute, context):
        attribute_list, condition_attribute = context
        if self._should_add_base_on_condition(attribute, condition_attribute):
            attribute_list.append(attribute)

    def _add_constructor(self):
        self._add_constructor_internal(None)

    def _add_constructor_internal(self, condition_attribute):
        constructor_method = TypescriptMethodGenerator('public', '', 'constructor', [self._create_param_list(condition_attribute)], None)
        if self.base_class_name is not None:
            constructor_method.add_instructions(
                ['super({0})'.format(self._create_list(self.base_class_name, self._add_to_variable, condition_attribute))])
            self.load_from_binary_atrribute_list.append(self._create_custom_variable_list(self.base_class_name,
                                                                                          self._add_to_variable, condition_attribute,
                                                                                          'superObject'))

        object_attributes = []
        self._recurse_foreach_attribute(self.name, self._add_attribute_to_list, (object_attributes, condition_attribute),
                                        [self.base_class_name, self._get_body_class_name()])
        # for attribute in object_attributes:
        #     if self._is_inline_class(attribute):
        #         continue
        #     if 'size' not in attribute or not is_builtin_type(attribute['type'], attribute['size']):
        #         constructor_method.add_instructions(['GeneratorUtils.notNull({0}, "{0} is null")'.format(attribute['name'])])

        for variable in object_attributes:
            if self._should_declaration(variable):
                if self._is_inline_class(variable):
                    constructor_method.add_instructions(
                        ['this.{0} = {1}.create({2})'.format(variable['name'],
                                                             get_generated_class_name(variable['type'], variable, self.schema),
                                                             self._create_list(variable['type'], self._add_to_variable,
                                                                               condition_attribute))])
                    self.load_from_binary_atrribute_list.append(self._create_custom_variable_list(variable['type'],
                                                                                                  self._add_to_variable, condition_attribute,
                                                                                                  variable['name']))
                    self._add_required_import(format_import(get_generated_class_name(variable['type'], variable, self.schema)))
                else:
                    constructor_method.add_instructions(['this.{0} = {0}'.format(variable['name'])])
                    self.load_from_binary_atrribute_list.append(variable['name'])

        if condition_attribute:
            condition_type_attribute = get_attribute_property_equal(self.schema, self.class_schema['layout'], 'name',
                                                                    condition_attribute['condition'], False)
            if condition_type_attribute:
                condition_type_value = '{0}.{1}'.format(
                    get_generated_class_name(condition_type_attribute['type'], condition_type_attribute, self.schema),
                    create_enum_name(condition_attribute['condition_value']))
                constructor_method.add_instructions(['this.{0} = {1}'.format(condition_attribute['condition'], condition_type_value)])
                code_lines = []
                self._init_other_attribute_in_condition(condition_attribute, 'this.', code_lines)
                constructor_method.add_instructions(code_lines)

        self._add_method_documentation(constructor_method, 'Constructor.', self._create_name_comment_list(self.name, condition_attribute),
                                       None)

        self._add_method(constructor_method)

    def _add_factory_method(self):
        self._add_factory_method_internal(None)

    def _add_factory_method_internal(self, condition_attribute):
        factory = TypescriptMethodGenerator('public', self.generated_class_name, 'create',
                                            [self._create_param_list(condition_attribute)], '',
                                            True)
        factory.add_instructions(['return new {0}({1})'.format(
            self.generated_class_name, self._create_list(self.name, self._add_to_variable, condition_attribute))])
        self._add_method_documentation(factory, 'Creates an instance of {0}.'.format(self.generated_class_name),
                                       self._create_name_comment_list(self.name, condition_attribute),
                                       'Instance of {0}.'.format(self.generated_class_name))
        self._add_method(factory)

    def _add_constructors(self):
        for attribute in self.condition_list:
            self._add_constructor_internal(attribute)

    def _add_factory_methods(self):
        for attribute in self.condition_list:
            self._add_factory_method_internal(attribute)

    @staticmethod
    def should_generate_class(name):
        return (name.startswith('Embedded')
                or name.endswith('Transaction')
                or name.startswith('Mosaic')
                or name.endswith('Mosaic')
                or name.endswith('Modification')
                or (name.endswith('Body') and name != 'EntityBody')
                or name.endswith('Cosignature'))
