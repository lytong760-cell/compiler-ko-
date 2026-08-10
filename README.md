# compiler-ko-

A compiler/interpreter for the `.ko` programming language (spec v2.800).

## Overview

`.ko` is a multi-paradigm programming language that supports imperative, object-oriented, and low-level memory manipulation paradigms. The compiler/interpreter (`ko_compiler.py`) provides a complete execution environment including:

- **Lexer & Parser**: Tokenizes and parses `.ko` source into an AST
- **Interpreter**: Direct AST execution (primary execution path)
- **Exception Handling**: Structured catch blocks with global upward catching (spec IX.2)
- **OOP Support**: Classes with private/public members, instantiation, and method dispatch
- **Data Structures**: Tuples, dictionaries, and indexing
- **System Tags**: `<printf>`, `<print>`, `<input>`, `<memory>`, `<now>`, `<encode>`, `<if>/<elif>/<else>`, `<return>`, `<for>`, `<loop>`
- **Module Imports**: `Random`, `Os`, `Website` modules with secure allowlisting

## Quick Start

```bash
# Run a .ko file
python3 ko_compiler.py demo.ko

# Run a test file
python3 ko_compiler.py test_simple.ko

# Run the test suite
python3 ko_compiler.py test_spec.ko
```

## Language Syntax

### Basic Types
- `int(10)~hp` — integer variable
- `freal(3.14)~pi` — float variable
- `string("hello")~name` — string variable
- `booling(\True\)~active` — boolean variable
- `byte("A")~ch` — byte variable
- `bytes("48656c6c6f")~data` — bytes variable

### Control Flow
- `<if>(condition) [ ... ]` — conditional
- `<elif>(condition) [ ... ]` — else-if
- `<else> [ ... ]` — else block
- `**Loop** <for>(~i=1&=5) [ ... ]` — for loop
- `**Loop** <for.f.whle>@also [ ... ]` — while loop

### Functions
```
func_name(int~param1, int~param2) [
    <return>(result)
]
```

### Classes
```
ClassName !class [
    @private [
        int(0)~hp
        take_damage(int~dmg) [ ... ]
    ]
]
```

### Exception Handling
```
<catch>(`ErrorCode`) [
    <printf>^("Caught error\n")
    <return>(0)
]
```

Catch blocks at global scope implement **Sequential Upward Catching** (spec IX.2): they protect all code before them in the same scope.

### Dictionaries
```
(1{'key'}, 2{'hp'})~dict
# Access: dict{'key'}
```

### Tuples
```
(1, 2, 3)~tuple
# Access: tuple<0>
```

### Module Imports
```
**Import**($Random)@also%~random!`global`:random
```

Allowed modules: `Random`, `Os`, `Website`

## Architecture

```
Source (.ko) → KoLexer → KoParser → AST (Program) → KoInterpreter (direct execution)
                                    → IRBuilder → IR module (for optimizer)
                                    → SemanticAnalyzer (type checking, scope resolution)
```

The interpreter is the primary execution path. The code generator (`KoCodeGenerator`), IR builder (`IRBuilder`), optimizer (`Optimizer`), and `SemanticAnalyzer` are fully integrated into the compilation pipeline for IR generation, optimization, and semantic validation.

### Key Classes

| Class | Role |
|-------|------|
| `KoLexer` | Tokenizes `.ko` source into `Token` stream |
| `KoParser` | Builds AST nodes (`Program`, `FuncDecl`, `ClassDecl`, `MainBlock`, `CatchStmt`, etc.) |
| `KoInterpreter` | Direct AST interpreter — primary execution engine |
| `KoCodeGenerator` | Generates Python code from AST (secondary, not used in main flow) |
| `IRBuilder` | Builds intermediate representation for optimization |
| `Optimizer` | Optimization passes (constant folding, dead code elimination, peephole) |
| `SemanticAnalyzer` | Semantic analysis (type checking, scope resolution) |

## Security

The interpreter includes source-level security validation:

- **Module allowlist**: Only `Random`, `Os`, `Website` modules can be imported
- **Banned URL schemes**: `file://` URLs are prohibited
- **Allowed URL schemes**: Only `http://` and `https://` are permitted
- **Dangerous function detection**: `exec()`, `eval()`, `__import__()`, `subprocess`, `os.system`, `shutil`, `pickle`, `shelve` are blocked
- **Path traversal detection**: `..` in import/file-open contexts is blocked
- **Duplicate declaration detection**: Nested and global duplicate function/class declarations are detected and reported as semantic errors

## Testing

- `test_simple.ko` — basic arithmetic regression test
- `test_functions.ko` — function declaration and call tests
- `test_control_flow.ko` — if/elif/else and loop tests
- `test_oop.ko` — class instantiation and method dispatch tests
- `test_catch_func.ko` — catch block with function call tests
- `test_imports_and_loops.ko` — module import and loop integration tests
- `test_data_structures.ko` — tuple and dictionary tests
- `test_system_tags.ko` — system tag integration tests
- `demo.ko` — full demo showcasing all v2.800 features
- `test_*.ko` — individual feature test files

## Known Limitations

- `web.domain` and `memory_addr`/`memory_free` are stub implementations in the interpreter
- `Import.java` and `Loop.cpp` subprocess calls are dead code (always fall back to Python)

## Recent Improvements

- **Class identity from enclosing context**: Nested classes now retain distinct enclosing-class identities in the IR module, preventing top-level classes from being self-qualified.
- **Nested declaration duplicate checks**: The semantic analyzer now detects and reports duplicate nested function and class declarations before registration.
- **Multi-index support**: Chained indexing expressions (e.g., `dic{1{'a'}}`) are correctly lowered to sequential `BINARY_SUBSCR` operations.
- **Collection literal retention**: `TupleLiteral` and `DictLiteral` branches now preserve ordered element/key-value temporaries for `BUILD_TUPLE` and `BUILD_MAP` instructions.
- **Qualified function resolution**: Call expressions resolve against the active declaration scope, ensuring emitted targets match `IRModule.functions` keys.
- **Local variable scoping**: Declarations inside function/method bodies populate `IRFunction.local_vars` instead of overwriting module-level entries.

## Spec Version

This implementation targets spec v2.800. The specification document (`đặc tả`) describes the full language design; this README reflects the actual implemented behavior.