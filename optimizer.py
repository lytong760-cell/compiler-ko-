from __future__ import annotations

from typing import Dict, List, Optional, Set


class ConstantFolder:
    def __init__(self) -> None:
        self.changes_made: bool = False

    def fold(self, module: object) -> object:
        from ir import IRFunction, IRBasicBlock, IROpcode, IRInstruction, IRType

        for func in module.functions.values():
            self._fold_function(func)
        if module.main:
            for bb in module.main:
                self._fold_basic_block(bb)
        for catch in module.catch_blocks:
            for bb in catch.body:
                self._fold_basic_block(bb)
        return module

    def _fold_function(self, func: IRFunction) -> None:
        for bb in func.body:
            self._fold_basic_block(bb)

    def _fold_basic_block(self, bb: IRBasicBlock) -> None:
        from ir import IROpcode
        i = 0
        while i < len(bb.instructions):
            instr = bb.instructions[i]
            if instr.opcode == IROpcode.BINARY_OP:
                folded = self._fold_binary_op(instr)
                if folded is not None:
                    bb.instructions[i] = folded
                    self.changes_made = True
            elif instr.opcode == IROpcode.UNARY_OP:
                folded = self._fold_unary_op(instr)
                if folded is not None:
                    bb.instructions[i] = folded
                    self.changes_made = True
            elif instr.opcode == IROpcode.LOAD_CONST:
                pass
            i += 1

    def _fold_binary_op(self, instr: IRInstruction) -> Optional[IRInstruction]:
        left = instr.arg
        right = instr.arg2

        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            op = instr.result
            if op == "+":
                return IRInstruction(IROpcode.LOAD_CONST, left + right, None, instr.result, instr.type, instr.line)
            elif op == "-":
                return IRInstruction(IROpcode.LOAD_CONST, left - right, None, instr.result, instr.type, instr.line)
            elif op == "*":
                return IRInstruction(IROpcode.LOAD_CONST, left * right, None, instr.result, instr.type, instr.line)
            elif op == "/":
                if right == 0:
                    return None
                return IRInstruction(IROpcode.LOAD_CONST, left / right, None, instr.result, instr.type, instr.line)
            elif op == "%":
                if right == 0:
                    return None
                return IRInstruction(IROpcode.LOAD_CONST, left % right, None, instr.result, instr.type, instr.line)
            elif op == "and":
                return IRInstruction(IROpcode.LOAD_CONST, bool(left and right), None, instr.result, instr.type, instr.line)
            elif op == "or":
                return IRInstruction(IROpcode.LOAD_CONST, bool(left or right), None, instr.result, instr.type, instr.line)
            elif op == "==":
                return IRInstruction(IROpcode.LOAD_CONST, left == right, None, instr.result, instr.type, instr.line)
            elif op == "!=":
                return IRInstruction(IROpcode.LOAD_CONST, left != right, None, instr.result, instr.type, instr.line)
            elif op == ">":
                return IRInstruction(IROpcode.LOAD_CONST, left > right, None, instr.result, instr.type, instr.line)
            elif op == ">=":
                return IRInstruction(IROpcode.LOAD_CONST, left >= right, None, instr.result, instr.type, instr.line)
            elif op == "<":
                return IRInstruction(IROpcode.LOAD_CONST, left < right, None, instr.result, instr.type, instr.line)
            elif op == "<=":
                return IRInstruction(IROpcode.LOAD_CONST, left <= right, None, instr.result, instr.type, instr.line)
        return None

    def _fold_unary_op(self, instr: IRInstruction) -> Optional[IRInstruction]:
        operand = instr.arg
        op = instr.result

        if isinstance(operand, (int, float)):
            if op == "-":
                return IRInstruction(IROpcode.LOAD_CONST, -operand, None, instr.result, instr.type, instr.line)
            elif op == "not":
                return IRInstruction(IROpcode.LOAD_CONST, not operand, None, instr.result, instr.type, instr.line)
        return None


class DeadCodeEliminator:
    def __init__(self) -> None:
        self.changes_made: bool = False

    def eliminate(self, module: object) -> object:
        from ir import IRFunction, IRBasicBlock

        for func in module.functions.values():
            self._eliminate_function(func)
        if module.main:
            for bb in module.main:
                self._eliminate_basic_block(bb)
        for catch in module.catch_blocks:
            for bb in catch.body:
                self._eliminate_basic_block(bb)
        return module

    def _eliminate_function(self, func: IRFunction) -> None:
        for bb in func.body:
            self._eliminate_basic_block(bb)

    def _eliminate_basic_block(self, bb: IRBasicBlock) -> None:
        from ir import IROpcode
        new_instructions: List[IRInstruction] = []
        for instr in bb.instructions:
            if instr.is_dead:
                self.changes_made = True
                continue
            if instr.opcode == IROpcode.POP_TOP:
                prev = new_instructions[-1] if new_instructions else None
                if prev and prev.opcode in (IROpcode.LOAD_CONST, IROpcode.LOAD_NAME):
                    self.changes_made = True
                    new_instructions.pop()
                    continue
            new_instructions.append(instr)
        bb.instructions = new_instructions

    def remove_unused_variables(self, module: object) -> object:
        used_vars: Set[str] = set()

        for func in module.functions.values():
            self._collect_used_vars_in_function(func, used_vars)
        if module.main:
            for bb in module.main:
                self._collect_used_vars_in_block(bb, used_vars)

        for name, var in module.global_vars.items():
            if name not in used_vars and not name.startswith("_"):
                var.defined = False
                self.changes_made = True

        return module

    def _collect_used_vars_in_function(self, func: IRFunction, used: Set[str]) -> None:
        for bb in func.body:
            self._collect_used_vars_in_block(bb, used)

    def _collect_used_vars_in_block(self, bb: IRBasicBlock, used: Set[str]) -> None:
        from ir import IROpcode
        for instr in bb.instructions:
            if instr.opcode == IROpcode.LOAD_NAME:
                used.add(str(instr.arg))
            elif instr.opcode == IROpcode.CALL_FUNCTION:
                used.add(str(instr.arg))


class PeepholeOptimizer:
    def __init__(self) -> None:
        self.changes_made: bool = False

    def optimize(self, module: object) -> object:
        from ir import IRFunction, IRBasicBlock

        for func in module.functions.values():
            self._optimize_function(func)
        if module.main:
            for bb in module.main:
                self._optimize_basic_block(bb)
        for catch in module.catch_blocks:
            for bb in catch.body:
                self._optimize_basic_block(bb)
        return module

    def _optimize_function(self, func: IRFunction) -> None:
        for bb in func.body:
            self._optimize_basic_block(bb)

    def _optimize_basic_block(self, bb: IRBasicBlock) -> None:
        from ir import IROpcode
        instructions = bb.instructions
        changed = True
        while changed:
            changed = False
            new_instructions: List[IRInstruction] = []
            i = 0
            while i < len(instructions):
                if i + 1 < len(instructions):
                    curr = instructions[i]
                    next_instr = instructions[i + 1]

                    result = self._try_peephole(curr, next_instr)
                    if result is not None:
                        new_instructions.append(result)
                        i += 2
                        changed = True
                        continue

                new_instructions.append(instructions[i])
                i += 1
            instructions = new_instructions
        bb.instructions = instructions

    def _try_peephole(self, a: IRInstruction, b: IRInstruction) -> Optional[IRInstruction]:
        from ir import IROpcode, IRType

        if a.opcode == IROpcode.LOAD_CONST and b.opcode == IROpcode.BINARY_OP:
            if b.arg2 == a.result and b.result == a.result:
                if b.result == "+":
                    return IRInstruction(IROpcode.LOAD_CONST, a.arg, None, b.result, b.type, a.line)
                elif b.result == "*" and a.arg == 1:
                    return IRInstruction(IROpcode.LOAD_CONST, a.arg, None, b.result, b.type, a.line)
                elif b.result == "*" and a.arg == 0:
                    return IRInstruction(IROpcode.LOAD_CONST, 0, None, b.result, b.type, a.line)
        return None


class Optimizer:
    def __init__(self, enable_constant_folding: bool = True,
                 enable_dead_code_elimination: bool = True,
                 enable_peephole: bool = True) -> None:
        self.constant_folder = ConstantFolder()
        self.dead_code_eliminator = DeadCodeEliminator()
        self.peephole_optimizer = PeepholeOptimizer()
        self.enable_constant_folding = enable_constant_folding
        self.enable_dead_code_elimination = enable_dead_code_elimination
        self.enable_peephole = enable_peephole
        self.optimization_passes: List[str] = []

    def optimize(self, module: object) -> object:
        self.optimization_passes = []

        if self.enable_constant_folding:
            self.constant_folder.fold(module)
            if self.constant_folder.changes_made:
                self.optimization_passes.append("constant_folding")

        if self.enable_dead_code_elimination:
            self.dead_code_eliminator.eliminate(module)
            if self.dead_code_eliminator.changes_made:
                self.optimization_passes.append("dead_code_elimination")

        if self.enable_peephole:
            self.peephole_optimizer.optimize(module)
            if self.peephole_optimizer.changes_made:
                self.optimization_passes.append("peephole_optimization")

        return module

    def get_report(self) -> str:
        if not self.optimization_passes:
            return "No optimizations applied."
        return "Optimization passes applied: " + ", ".join(self.optimization_passes)