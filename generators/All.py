from generators.cpp_builder.BuilderGenerator import BuilderGenerator
from generators.java.JavaFileGenerator import JavaFileGenerator
from generators.typescript.TypescriptFileGenerator import TypescriptFileGenerator

AVAILABLE_GENERATORS = {
    'cpp_builder': BuilderGenerator,
    'java': JavaFileGenerator,
    'typescript': TypescriptFileGenerator
}
