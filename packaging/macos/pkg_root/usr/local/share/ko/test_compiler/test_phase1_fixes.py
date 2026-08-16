#!/usr/bin/env python3
"""Test script for Phase 1 compiler correctness fixes."""
import sys
sys.path.insert(0, '/workspaces/compiler-ko-')

from ko_compiler import (
    KoLexer, KoParser, KoInterpreter, 
    CatchStmt, DictLiteral, Indexing, Literal, Identifier,
    IRBuilder
)

def test_catch_stmt_error_condition():
    """Test that CatchStmt.error_condition stores backtick-wrapped error codes."""
    print("Testing CatchStmt.error_condition...")
    catch = CatchStmt("`DivideByZeroError`", [])
    assert catch.error_condition == "`DivideByZeroError`", f"Expected '`DivideByZeroError`', got {catch.error_condition}"
    # Test that the interpreter strips backticks correctly
    error_code = catch.error_condition.strip("`")
    assert error_code == "DivideByZeroError", f"Expected 'DivideByZeroError', got {error_code}"
    print("  PASS")

def test_nested_dict_indexing():
    """Test that dic{1{'a'}} parses as nested indexing, not dict literal."""
    print("Testing nested dictionary indexing...")
    source = 'dic{1{\'a\'}}'
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    parser = KoParser(tokens)
    expr = parser.parse_expression()
    
    print(f"  Parsed expr: {expr}")
    print(f"  Type: {type(expr)}")
    if isinstance(expr, Indexing):
        print(f"  Target: {expr.target} (type: {type(expr.target)})")
        print(f"  Index: {expr.index}")
    
    # Should be Indexing(dic, [Indexing(1, ['a'])])
    assert isinstance(expr, Indexing), f"Expected Indexing, got {type(expr)}"
    assert isinstance(expr.target, Identifier), f"Expected Identifier, got {type(expr.target)}"
    assert expr.target.name == "dic", f"Expected 'dic', got {expr.target.name}"
    assert len(expr.index) == 1, f"Expected 1 index, got {len(expr.index)}"
    nested = expr.index[0]
    assert isinstance(nested, Indexing), f"Expected nested Indexing, got {type(nested)}"
    assert isinstance(nested.target, Literal), f"Expected Literal, got {type(nested.target)}"
    assert nested.target.value == 1, f"Expected 1, got {nested.target.value}"
    assert len(nested.index) == 1, f"Expected 1 index, got {len(nested.index)}"
    assert isinstance(nested.index[0], Literal), f"Expected Literal, got {type(nested.index[0])}"
    assert nested.index[0].value == 'a', f"Expected 'a', got {nested.index[0].value}"
    print("  PASS")

def test_ir_emit_binary_op():
    """Test that emit_binary_op emits only one instruction."""
    print("Testing IR emit_binary_op...")
    builder = IRBuilder()
    builder.start_block("test_block")
    builder.emit_binary_op("+", "_t_left", "_t_right", "_t_result")
    # Should emit exactly 1 instruction
    assert len(builder.current_block.instructions) == 1, f"Expected 1 instruction, got {len(builder.current_block.instructions)}"
    instr = builder.current_block.instructions[0]
    assert instr.opcode.name == "BINARY_OP", f"Expected BINARY_OP, got {instr.opcode}"
    assert instr.arg == "+", f"Expected '+', got {instr.arg}"
    assert instr.arg2 == "_t_right", f"Expected '_t_right', got {instr.arg2}"
    print("  PASS")

def test_dict_literal_in_indexing():
    """Test that dict literals can still be created at expression level."""
    print("Testing dict literal creation...")
    source = '{1: \'a\'}'
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    parser = KoParser(tokens)
    expr = parser.parse_expression()
    
    assert isinstance(expr, DictLiteral), f"Expected DictLiteral, got {type(expr)}"
    assert len(expr.mapping) == 1, f"Expected 1 mapping, got {len(expr.mapping)}"
    print("  PASS")

def test_literal_brace_at_top_level():
    """Test that literal{value} creates DictLiteral at top level."""
    print("Testing literal{value} at top level...")
    source = '1{\'a\'}'
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    parser = KoParser(tokens)
    expr = parser.parse_expression()
    
    print(f"  Parsed expr: {expr}")
    print(f"  Type: {type(expr)}")
    
    # Should be DictLiteral({1: 'a'})
    assert isinstance(expr, DictLiteral), f"Expected DictLiteral, got {type(expr)}"
    assert len(expr.mapping) == 1, f"Expected 1 mapping, got {len(expr.mapping)}"
    print("  PASS")

def test_scope_lookup():
    """Test that scope lookup works correctly."""
    print("Testing scope lookup...")
    source = '''
    [
        int(10)~x
        int(20)~y
        <printf>^("{x} {y}\\n")
    ]
    '''
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    parser = KoParser(tokens)
    program = parser.parse()
    
    interpreter = KoInterpreter(program)
    # This should not raise NameError for x or y
    try:
        interpreter.run()
        print("  PASS")
    except NameError as e:
        print(f"  FAIL: {e}")
        return False
    return True

if __name__ == "__main__":
    test_catch_stmt_error_condition()
    test_nested_dict_indexing()
    test_ir_emit_binary_op()
    test_dict_literal_in_indexing()
    test_literal_brace_at_top_level()
    test_scope_lookup()
    print("\nAll tests completed!")
