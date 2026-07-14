from blueprint_dsl import (
    BLUEPRINT_COMPILER_VERSION,
    BLUEPRINT_LANGUAGE_VERSION,
    BlueprintCompileError,
    CompiledBlueprint,
    StructuredOutputDslError,
    __version__,
    compile_blueprint,
)


def test_public_blueprint_api_preserves_the_established_compiler() -> None:
    compiled = compile_blueprint("Return OCR:\n  transcription: String")

    assert isinstance(compiled, CompiledBlueprint)
    assert compiled.name == "o_c_r"
    assert BlueprintCompileError is StructuredOutputDslError
    assert BLUEPRINT_COMPILER_VERSION == __version__ == "0.1.0"
    assert BLUEPRINT_LANGUAGE_VERSION == "blueprint/1"
