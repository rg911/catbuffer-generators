from enum import Enum


class TypeDescriptorDisposition(Enum):
    Inline = 'inline'
    Const = 'const'


def indent(code, n_indents=1):
    indented = ' ' * 4 * n_indents + code
    return indented


def get_attribute_property_equal(schema, attribute_list, attribute_name, attribute_value, recurse=True):
    for current_attribute in attribute_list:
        if attribute_name in current_attribute and current_attribute[attribute_name] == attribute_value:
            return current_attribute
        if (recurse and 'disposition' in current_attribute and
                current_attribute['disposition'] == TypeDescriptorDisposition.Inline.value):
            value = get_attribute_property_equal(schema, schema[current_attribute['type']]['layout'], attribute_name, attribute_value)
            if value is not None:
                return value
    return None


def get_attribute_if_size(attribute_name, attributes, schema):
    value = get_attribute_property_equal(schema, attributes, 'size', attribute_name)
    return value['name'] if value is not None else None


def get_builtin_type(size):
    if size == 8:
        return 'number[]'
    return 'number'


def get_read_method_name(size):
    if isinstance(size, str) or size > 8:
        method_name = 'readFully'
    else:
        method_name = 'GeneratorUtils.uint64ToBuffer' if size == 8 else 'GeneratorUtils.uintToBuffer'
    return method_name


def get_byte_convert_method_name(size):
    if isinstance(size, str) or size > 8:
        method_name = ''
    else:
        method_name = 'GeneratorUtils.bufferToUint64({0})' if size == 8 else 'GeneratorUtils.bufferToUint({0})'
    return method_name


def get_generated_type(schema, attribute):
    typename = attribute['type']
    attribute_type = get_real_attribute_type(attribute)
    if attribute_type == AttributeType.SIMPLE:
        return get_builtin_type(get_attribute_size(schema, attribute))
    if attribute_type == AttributeType.BUFFER:
        return 'Uint8Array'

    if not is_byte_type(typename):
        typename = get_generated_class_name(typename, attribute, schema)

    if attribute_type == AttributeType.ARRAY:
        return '{0}[]'.format(typename)
    if attribute_type == AttributeType.FLAGS:
        return '{0}'.format(typename)

    return typename


def get_comment_from_name(name):
    return name[0].upper() + ''.join(' ' + x.lower() if x.isupper() else x for x in name[1:])


def append_period_if_needed(line):
    return line if line.endswith('.') else line + '.'


def get_comments_if_present(comment):
    if comment:
        return '/** {0} */'.format(format_description(comment))
    return None


def format_description(description):
    formated_description = description[0].upper() + description[1:]
    return append_period_if_needed(formated_description)


def create_enum_name(name):
    enum_name = name[0] + ''.join('_' + x if x.isupper() else x for x in name[1:])
    return enum_name.upper()


def get_comments_from_attribute(attribute, formatted=True):
    comment_text = attribute['comments'].strip() if 'comments' in attribute else ''
    if not comment_text and 'name' in attribute:
        comment_text = get_comment_from_name(attribute['name'])
    return get_comments_if_present(comment_text) if formatted else comment_text


def get_class_type_from_name(type_name):
    return '{0}.ts'.format(type_name)


def get_default_value(attribute):
    attribute_type = get_real_attribute_type(attribute)
    if attribute_type == AttributeType.SIMPLE:
        return '0'
    return 'null'


def format_import(attribute_type):
    return '{{ {0} }} from \'./{0}\''.format(attribute_type).replace('[]', '')


class TypeDescriptorType(Enum):
    """Type descriptor enum for Typescript generator"""
    Byte = 'byte'
    Struct = 'struct'
    Enum = 'enum'


def get_generated_class_name(typename, class_schema, schema):
    class_type_name = class_schema['type']
    default_name = typename + 'Dto'
    if is_byte_type(class_type_name) or is_enum_type(class_type_name) or typename not in schema:
        return default_name
    return typename + 'Builder' if is_struct_type(schema[typename]['type']) else default_name


def is_builtin_type(typename, size):
    # byte up to long are passed as 'byte' with size set to proper value
    return not isinstance(size, str) and is_byte_type(typename) and size <= 8


def is_enum_type(typename):
    return typename == TypeDescriptorType.Enum.value


def is_struct_type(typename):
    return typename == TypeDescriptorType.Struct.value


def is_byte_type(typename):
    return typename == TypeDescriptorType.Byte.value


class AttributeType(Enum):
    """Attribute type enumerables"""
    SIMPLE = 1

    BUFFER = 2

    ARRAY = 3

    CUSTOM = 4

    FLAGS = 5

    ENUM = 6

    UNKNOWN = 100


def get_attribute_size(schema, attribute_value):
    if 'size' not in attribute_value and not is_byte_type(attribute_value['type']) and not is_enum_type(attribute_value['type']):
        attr = schema[attribute_value['type']]
        if 'size' in attr:
            return attr['size']
        return 1
    return attribute_value['size']


def get_real_attribute_type(attribute):
    attribute_type = attribute['type']

    if is_flags_enum(attribute_type):
        return AttributeType.FLAGS

    if is_struct_type(attribute_type) or 'size' not in attribute:
        return AttributeType.CUSTOM

    if is_enum_type(attribute_type):
        return AttributeType.ENUM

    if 'size' in attribute:
        attribute_size = attribute['size']
        att_kind = AttributeType.BUFFER
        if isinstance(attribute_size, str):
            if attribute_size.endswith('Size'):
                att_kind = AttributeType.BUFFER
            if attribute_size.endswith('Count'):
                att_kind = AttributeType.ARRAY
            return att_kind
        if is_builtin_type(attribute_type, attribute_size):
            return AttributeType.SIMPLE
    return AttributeType.BUFFER


def is_flags_enum(name):
    return name.endswith('Flags')
