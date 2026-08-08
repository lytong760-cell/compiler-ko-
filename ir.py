from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class IROpcode(Enum):
    LOAD_CONST = "LOAD_CONST"
    LOAD_NAME = "LOAD_NAME"
    STORE_NAME = "STORE_NAME"
    BINARY_OP = "BINARY_OP"
    UNARY_OP = "UNARY_OP"
    COMPARE_OP = "COMPARE_OP"
    POP_JUMP_IF_FALSE = "POP_JUMP_IF_FALSE"
    JUMP_FORWARD = "JUMP_FORWARD"
    JUMP_ABSOLUTE = "JUMP_ABSOLUTE"
    POP_TOP = "POP_TOP"
    PRINT_EXPR = "PRINT_EXPR"
    PRINT_FORMAT = "PRINT_FORMAT"
    INPUT_CALL = "INPUT_CALL"
    CALL_FUNCTION = "CALL_FUNCTION"
    RETURN_VALUE = "RETURN_VALUE"
    BUILD_TUPLE = "BUILD_TUPLE"
    BUILD_MAP = "BUILD_MAP"
    BUILD_LIST = "BUILD_LIST"
    BINARY_SUBSCR = "BINARY_SUBSCR"
    STORE_SUBSCR = "STORE_SUBSCR"
    LOAD_ATTR = "LOAD_ATTR"
    STORE_ATTR = "STORE_ATTR"
    NOP = "NOP"
    DELETE_NAME = "DELETE_NAME"
    UNPACK_SEQUENCE = "UNPACK_SEQUENCE"
    ROT_TWO = "ROT_TWO"
    DUP_TOP = "DUP_TOP"
    JUMP_IF_TRUE_OR_POP = "JUMP_IF_TRUE_OR_POP"
    JUMP_IF_FALSE_OR_POP = "JUMP_IF_FALSE_OR_POP"


class IRType(Enum):
    INT = "int"
    FREAL = "freal"
    STRING = "string"
    BOOL = "booling"
    BYTE = "byte"
    BYTES = "bytes"
    TUPLE = "tuple"
    DICT = "dict"
    LIST = "list"
    NONE = "none"
    UNKNOWN = "unknown"


@dataclass
class IRConstant:
    value: Any
    ir_type: IRType = IRType.UNKNOWN


@dataclass
class IRVariable:
    name: str
    ir_type: IRType = IRType.UNKNOWN
    defined: bool = False
    used: bool = False


@dataclass
class IRInstruction:
    opcode: IROpcode
    arg: Any = None
    arg2: Any = None
    result: Optional[str] = None
    type: IRType = IRType.UNKNOWN
    line: int = 0
    is_dead: bool = False
    op: Optional[str] = None


@dataclass
class IRBasicBlock:
    name: str
    instructions: List[IRInstruction] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)


@dataclass
class IRFunction:
    name: str
    params: List[IRVariable]
    body: List[IRBasicBlock]
    return_type: IRType = IRType.UNKNOWN
    local_vars: Dict[str, IRVariable] = field(default_factory=dict)
    is_method: bool = False
    is_private: bool = False
    captured_vars: List[str] = field(default_factory=list)


@dataclass
class IRClass:
    name: str
    fields: Dict[str, IRVariable]
    methods: Dict[str, IRFunction]
    private_fields: Dict[str, IRVariable] = field(default_factory=dict)
    private_methods: Dict[str, IRFunction] = field(default_factory=dict)


@dataclass
class IRImport:
    module_name: str
    alias: str
    scope_tag: str


@dataclass
class IRCatchBlock:
    error_code: Optional[str]
    condition: Optional[str]
    body: List[IRBasicBlock]


@dataclass
class IRModule:
    imports: List[IRImport] = field(default_factory=list)
    functions: Dict[str, IRFunction] = field(default_factory=dict)
    classes: Dict[str, IRClass] = field(default_factory=dict)
    main: Optional[List[IRBasicBlock]] = None
    catch_blocks: List[IRCatchBlock] = field(default_factory=list)
    global_vars: Dict[str, IRVariable] = field(default_factory=dict)


class IRBuilder:
    def __init__(self):
        self.module = IRModule()
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.basic_blocks: List[IRBasicBlock] = []
        self.current_block: Optional[IRBasicBlock] = None
        self.instruction_counter: int = 0
        self.temp_counter: int = 0
        self.scope_stack: List[str] = ["global"]
        self.local_vars: Dict[str, IRVariable] = {}

    def new_temp(self) -> str:
        self.temp_counter += 1
        return f"_t{self.temp_counter}"

    def new_label(self, prefix: str = "L") -> str:
        self.instruction_counter += 1
        return f"{prefix}_{self.instruction_counter}"

    def emit(self, opcode: IROpcode, arg: Any = None, arg2: Any = None,
             result: Optional[str] = None, ir_type: IRType = IRType.UNKNOWN,
             line: int = 0, op: Optional[str] = None) -> IRInstruction:
        instr = IRInstruction(
            opcode=opcode, arg=arg, arg2=arg2,
            result=result, type=ir_type, line=line, is_dead=False, op=op
        )
        if self.current_block is not None:
            self.current_block.instructions.append(instr)
        return instr

    def emit_constant(self, value: Any, ir_type: IRType = IRType.UNKNOWN, line: int = 0) -> str:
        result = self.new_temp()
        self.emit(IROpcode.LOAD_CONST, value, None, result, ir_type, line)
        return result

    def emit_load(self, name: str, ir_type: IRType = IRType.UNKNOWN, line: int = 0) -> str:
        result = self.new_temp()
        self.emit(IROpcode.LOAD_NAME, name, None, result, ir_type, line)
        return result

    def emit_store(self, name: str, value: str, ir_type: IRType = IRType.UNKNOWN, line: int = 0) -> None:
        self.emit(IROpcode.STORE_NAME, name, value, None, ir_type, line)

    def emit_binary_op(self, op: str, left: str, right: str,
                       result: str, ir_type: IRType = IRType.UNKNOWN, line: int = 0) -> None:
        # Single BINARY_OP instruction: arg = left, arg2 = right, result = destination temp, op = operator
        self.emit(IROpcode.BINARY_OP, left, right, result, ir_type, line, op=op)

    def emit_unary_op(self, op: str, operand: str,
                      result: str, ir_type: IRType = IRType.UNKNOWN, line: int = 0) -> None:
        self.emit(IROpcode.UNARY_OP, operand, None, result, ir_type, line, op=op)

    def emit_call(self, func_name: str, args: List[str], result: Optional[str],
                  ir_type: IRType = IRType.UNKNOWN, line: int = 0) -> None:
        self.emit(IROpcode.CALL_FUNCTION, func_name, args, result, ir_type, line)

    def emit_return(self, value: Optional[str] = None, line: int = 0) -> None:
        self.emit(IROpcode.RETURN_VALUE, value, None, None, IRType.NONE, line)

    def emit_print(self, value: str, line: int = 0) -> None:
        self.emit(IROpcode.PRINT_EXPR, value, None, None, IRType.NONE, line)

    def emit_printf(self, format_parts: List[str], args: List[str], line: int = 0) -> None:
        self.emit(IROpcode.PRINT_FORMAT, format_parts, args, None, IRType.NONE, line)

    def emit_input(self, prompt: str, result: str, line: int = 0) -> None:
        self.emit(IROpcode.INPUT_CALL, prompt, None, result, IRType.STRING, line)

    def emit_jump_if_false(self, condition: str, target: str, line: int = 0) -> None:
        self.emit(IROpcode.POP_JUMP_IF_FALSE, condition, target, None, IRType.NONE, line)

    def emit_jump(self, target: str, line: int = 0) -> None:
        self.emit(IROpcode.JUMP_FORWARD, target, None, None, IRType.NONE, line)

    def emit_jump_absolute(self, target: str, line: int = 0) -> None:
        self.emit(IROpcode.JUMP_ABSOLUTE, target, None, None, IRType.NONE, line)

    def emit_pop(self, line: int = 0) -> None:
        self.emit(IROpcode.POP_TOP, None, None, None, IRType.NONE, line)

    def emit_nop(self, line: int = 0) -> None:
        self.emit(IROpcode.NOP, None, None, None, IRType.NONE, line)

    def emit_binary_subscr(self, target: str, index: str, result: str,
                           ir_type: IRType = IRType.UNKNOWN, line: int = 0) -> None:
        self.emit(IROpcode.BINARY_SUBSCR, target, index, result, ir_type, line)

    def emit_store_subscr(self, target: str, index: str, value: str, line: int = 0) -> None:
        self.emit(IROpcode.STORE_SUBSCR, target, index, value, IRType.NONE, line)

    def start_block(self, name: str) -> IRBasicBlock:
        block = IRBasicBlock(name)
        self.basic_blocks.append(block)
        self.current_block = block
        return block

    def end_block(self) -> None:
        self.current_block = None

    def connect_blocks(self, from_block: str, to_block: str) -> None:
        for bb in self.basic_blocks:
            if bb.name == from_block and to_block not in bb.successors:
                bb.successors.append(to_block)
            if bb.name == to_block and from_block not in bb.predecessors:
                bb.predecessors.append(from_block)

    def build_module(self) -> IRModule:
        return self.module


def ir_to_string(module: IRModule) -> str:
    lines: List[str] = []
    lines.append("=== IR Module ===")
    for imp in module.imports:
        lines.append(f"  IMPORT {imp.module_name} AS {imp.alias} (scope={imp.scope_tag})")
    for name, func in module.functions.items():
        lines.append(f"  FUNCTION {name}({[p.name for p in func.params]}) -> {func.return_type.value}")
        for bb in func.body:
            lines.append(f"    BLOCK {bb.name}:")
            for instr in bb.instructions:
                op_display = f" {instr.op} " if instr.op else " "
                lines.append(f"      {instr.opcode.value} {instr.arg}{op_display}{instr.arg2} -> {instr.result} [{instr.type.value}]")
    for name, cls in module.classes.items():
        lines.append(f"  CLASS {name}")
        for fname, field in cls.fields.items():
            lines.append(f"    FIELD {fname}: {field.ir_type.value}")
        for mname, method in cls.methods.items():
            lines.append(f"    METHOD {mname}({[p.name for p in method.params]})")
    if module.main:
        lines.append("  MAIN:")
        for bb in module.main:
            lines.append(f"    BLOCK {bb.name}:")
            for instr in bb.instructions:
                op_display = f" {instr.op} " if instr.op else " "
                lines.append(f"      {instr.opcode.value} {instr.arg}{op_display}{instr.arg2} -> {instr.result} [{instr.type.value}]")
    for catch in module.catch_blocks:
        lines.append(f"  CATCH ({catch.error_code or catch.condition}):")
        for bb in catch.body:
            lines.append(f"    BLOCK {bb.name}:")
            for instr in bb.instructions:
                op_display = f" {instr.op} " if instr.op else " "
                lines.append(f"      {instr.opcode.value} {instr.arg}{op_display}{instr.arg2} -> {instr.result}")
    return "\n".join(lines)