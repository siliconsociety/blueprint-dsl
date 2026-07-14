"""Compile Blueprint structured-output contracts to strict JSON Schema."""

from importlib.metadata import version

from blueprint_dsl.compiler import (
    BLUEPRINT_DECLARATION_KEYWORDS,
    BLUEPRINT_SPEC_EXAMPLE,
    BLUEPRINT_TYPE_REGISTRY,
    BlueprintTypeInfo,
    CompiledStructuredOutputSchema,
    StructuredOutputDslError,
    blueprint_editor_metadata,
    blueprint_spec_card,
    blueprint_types_by_category,
    compile_structured_output_dsl,
)

__version__ = version("blueprint-dsl")
BLUEPRINT_LANGUAGE_VERSION = "blueprint/1"
BLUEPRINT_COMPILER_VERSION = __version__

BlueprintCompileError = StructuredOutputDslError
CompiledBlueprint = CompiledStructuredOutputSchema
compile_blueprint = compile_structured_output_dsl

__all__ = [
    "BLUEPRINT_COMPILER_VERSION",
    "BLUEPRINT_DECLARATION_KEYWORDS",
    "BLUEPRINT_LANGUAGE_VERSION",
    "BLUEPRINT_SPEC_EXAMPLE",
    "BLUEPRINT_TYPE_REGISTRY",
    "BlueprintCompileError",
    "BlueprintTypeInfo",
    "CompiledBlueprint",
    "CompiledStructuredOutputSchema",
    "StructuredOutputDslError",
    "__version__",
    "blueprint_editor_metadata",
    "blueprint_spec_card",
    "blueprint_types_by_category",
    "compile_blueprint",
    "compile_structured_output_dsl",
]
