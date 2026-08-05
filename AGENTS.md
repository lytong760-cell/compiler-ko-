# AGENTS.md — .ko Compiler Repository

## Project Overview

This is a compiler/interpreter for the `.ko` programming language (spec v2.800). The main entry point is `ko_compiler.py` (~2926 lines), which contains the lexer, parser, AST, code generator (outputs Python), and a built-in interpreter. Supporting modules: `ir.py`, `optimizer.py`, `semantic_analyzer.py`.

## Key Commands

- **Run a .ko file**: `python3 ko_compiler.py <file.ko>`
- **Run baseline tests**: `python3 ko_compiler.py test_simple.ko`
- **Run demo**: `python3 ko_compiler.py demo.ko`
- **Check syntax**: `python3 -c "import ast; ast.parse(open('ko_compiler.py').read())"`

## Architecture

```
Source (.ko) → KoLexer → KoParser → AST (Program) → KoCodeGenerator → Python code → execute
                                    → KoInterpreter (direct execution, no code gen)
                                    → IRBuilder → IR module (for optimizer)
```

- `KoLexer` — tokenizes .ko source into `Token` stream
- `KoParser` — builds AST nodes (`Program`, `FuncDecl`, `ClassDecl`, `MainBlock`, `CatchStmt`, etc.)
- `KoCodeGenerator` — visits AST, emits Python code as strings; also has `generate()` which produces a complete `.py` file
- `KoInterpreter` — direct AST interpreter (used for `run_ko_source`); has its own scope stack, function table, class table
- `IRBuilder` — builds intermediate representation for optimization passes

## Language Syntax Highlights

- **Blocks**: `[ ]` for executable code, `( )` for params/data, `{ }` for dicts
- **Sigil**: `~` before variable/function/class names (`int(10)~hp`)
- **System tags**: `<printf>`, `<input>`, `<memory>`, `<now>`, `<catch>`, `<encode>`, `<if>`, `<elif>`, `<else>`, `<return>`, `<for>`, `<print>`
- **Comments**: `| comment |`
- **Boolean literals**: `\True\`, `\False\` (backslash-wrapped)
- **Keywords**: `**Loop**`, `**Import**` must be bolded; bare `Loop`/`Import` are identifiers
- **Scope tags**: backtick-wrapped (`` `global` ``, `` `func` ``, `` `class` ``)
- **Instance pointer**: `$` prefix (`$p1~take_damage()`)
- **Indexing**: `<index>` for lists/tuples, `{key}` for dicts
- **Catch blocks**: `` `ErrorCode` `` for named errors, or expressions for conditions
- **Global scope constraint**: only `Import`, `FuncDecl`, `ClassDecl` allowed at top level; executable statements must be inside `[ ]` or a function

## Important Implementation Details

- **Circular imports avoided** via lazy imports inside methods (e.g., `import subprocess` inside `generate()`)
- **Import subsystem**: tries `Import.java` → `ImportEngine` (C++) → Python fallback (`_resolve_import_python`)
- **Loop subsystem**: tries `Loop` binary (C++) → Python `range()` fallback
- **Exception mapping**: `_ko_error_to_python()` maps .ko error codes to Python exception classes; `_map_python_error()` maps Python exceptions back to .ko error codes
- **Dictionary key access**: `dic{key}` → `Indexing(expr, [key])` → `_ko_dict_get(target, index, KeyNotFoundError)` in generated Python
- **Catch block scoping**: `_collect_catch_blocks()` gathers all catch blocks in a scope; `_handle_catch_in_scope()` matches by error code string (stripping backticks)
- **Class instantiation**: `~ClassName~instance` → `VarDecl` with `is_instantiation=True` → `ClassName()` in Python
- **Instance method dispatch**: `getattr(cls, method_name)(obj, *args)` where `cls` is looked up from `self.classes`

## Known Bugs / Incomplete Features

- `KoInterpreter.visit_FuncDecl` is missing — nested function declarations raise `NotImplementedError`
- `_handle_catch_in_scope` line 2022 references `catch.condition` but `CatchStmt` has `error_condition` (AttributeError for condition-based catches)
- `visit_WhileLoop` uses hardcoded `max_iterations = 100000` instead of `MAX_LOOP_ITERATIONS` (1000000)
- `visit_Call` instance method lookup uses `self.scopes[-1]` instead of `self.get_var()` — misses outer-scope variables
- Dictionary literal `:` syntax for multiple key-value pairs fails in parser
- Nested dictionary indexing `dic{1{'a'}}` parses as `dic[1['a']]` instead of `dic[1]['a']`
- `web.domain`, `memory_addr`, `memory_free` are stubs in the interpreter
- `Import.java` and `Loop.cpp` subprocess calls are dead code (always fall back to Python)

## Testing

- `test_simple.ko` — basic arithmetic test (passes)
- `test_spec.ko` — empty (0 bytes), needs content
- `demo.ko` — full demo with all v2.800 features; requires `web.domain` to be defined or mocked
- Test files created during debugging: `test_catch_func.ko`, `test_catch_cond.ko`, `test_dict*.ko` (can be cleaned up)

## File Ownership

| File | Role |
|------|------|
| `ko_compiler.py` | Main compiler: lexer, parser, AST, code generator, interpreter, IR builder |
| `ir.py` | IR definitions (instructions, opcodes, types, basic blocks) |
| `optimizer.py` | Optimization passes (constant folding, dead code elimination, peephole) |
| `semantic_analyzer.py` | Semantic analysis (type checking, scope resolution) |
| `demo.ko` | Full demo program |
| `test_simple.ko` | Baseline regression test |
| `Import.java` | Java-based import subsystem (dead code in current flow) |
| `Loop.cpp` | C++ loop optimization subsystem (dead code in current flow) |
| `LoopEngine` | Compiled Loop.cpp binary (unused) |
| `a.out` | Legacy compiled binary (unused) |
