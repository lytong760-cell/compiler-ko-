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
```

The interpreter is the primary execution path. The code generator (`KoCodeGenerator`), IR builder (`IRBuilder`), optimizer (`Optimizer`), and `SemanticAnalyzer` are retained for reference but are not used in the main execution flow.

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

## Testing

- `test_simple.ko` — basic arithmetic regression test
- `test_spec.ko` — comprehensive test suite with expected output
- `demo.ko` — full demo showcasing all v2.800 features
- `test_*.ko` — individual feature test files

## Known Limitations

- `KoInterpreter.visit_FuncDecl` is not implemented (nested function declarations raise `NotImplementedError`)
- `visit_WhileLoop` uses `MAX_LOOP_ITERATIONS` (1000000) correctly (previously hardcoded to 100000)
- `visit_CatchStmt` in the interpreter is a no-op (catch blocks are handled by `_handle_catch_in_scope`)
- `web.domain` and `memory_addr`/`memory_free` are stub implementations in the interpreter
- `Import.java` and `Loop.cpp` subprocess calls are dead code (always fall back to Python)
- Dictionary literal `:` syntax for multiple key-value pairs is now supported
- Tuple/dict declarations at global scope are now supported

## Spec Version

This implementation targets spec v2.800. The specification document (`đặc tả`) describes the full language design; this README reflects the actual implemented behavior.