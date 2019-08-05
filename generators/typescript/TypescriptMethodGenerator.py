from .Helpers import indent

class TypescriptMethodGenerator:
    """Typescript method generator"""

    def __init__(self, scope, return_type, name, params, exception_list='', static_method=False):
        # pylint: disable-msg=too-many-arguments
        self.name = name
        joint_list = ', '.join(params)
        constructor_params = []
        if name == 'constructor':
            for p in joint_list.split(','):
                constructor_params.append('{0}'.format(p))
        parameter = ', '.join(constructor_params) if name == 'constructor' else ', '.join(params)
        line = '{0} static'.format(scope) if static_method else '{0}'.format(scope)
        if return_type:
            line += ' {0}({1}): {2}'.format(self.name, parameter, return_type)
        else:
            line += ' {0}({1})'.format(self.name, parameter)
        if exception_list:
            line += ' {0}'.format(exception_list)
        line += ' {'
        self.method_output = [line]
        self.annotation_output = []
        self.documentation_output = []
        self._indent_num = 1

    def increment_indent(self):
        self._indent_num += 1

    def decrement_indent(self):
        self._indent_num -= 1

    def add_instructions(self, instructions, add_semicolon=True):
        for instruction in instructions:
            if add_semicolon:
                instruction += ';'
            self.method_output.append(indent(instruction, self._indent_num))

    def get_method(self):
        return self.documentation_output + self.annotation_output + self.method_output + ['}']

    def add_annotation(self, annotation):
        self.annotation_output.append(annotation)

    def add_documentations(self, documentations):
        for documentation in documentations:
            self.documentation_output.append(documentation)
