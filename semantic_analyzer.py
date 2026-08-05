from __future__ import annotations

from typing import Dict, List, Optional, Set


class SemanticScope:
    def __init__(self, name: str, parent: Optional["SemanticScope"] = None):
        self.name = name
        self.parent = parent
        self.variables: Dict[str, str] = {}
        self.functions: Dict[str, object] = {}
        self.classes: Dict[str, object] = {}
        self.imports: Dict[str, str] = {}

    def define_var(self, name: str, var_type: str) -> None:
        self.variables[name] = var_type

    def lookup_var(self, name: str) -> Optional[str]:
        scope = self
        while scope is not None:
            if name in scope.variables:
                return scope.variables[name]
            scope = scope.parent
        return None

    def define_func(self, name: str, func: object) -> None:
        self.functions[name] = func

    def lookup_func(self, name: str) -> Optional[object]:
        scope = self
        while scope is not None:
            if name in scope.functions:
                return scope.functions[name]
            scope = scope.parent
        return None

    def define_class(self, name: str, cls: object) -> None:
        self.classes[name] = cls

    def lookup_class(self, name: str) -> Optional[object]:
        scope = self
        while scope is not None:
            if name in scope.classes:
                return scope.classes[name]
            scope = scope.parent
        return None

    def define_import(self, alias: str, module_name: str) -> None:
        self.imports[alias] = module_name


class SemanticAnalyzer:
    ALLOWED_MODULES = {"Random", "Os", "Website"}

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.scope_stack: List[SemanticScope] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.in_private: bool = False
        self.loop_depth: int = 0
        self.return_count: int = 0
        self.function_return_type: Optional[str] = None

    def _push_scope(self, name: str) -> SemanticScope:
        parent = self.scope_stack[-1] if self.scope_stack else None
        scope = SemanticScope(name, parent)
        self.scope_stack.append(scope)
        return scope

    def _pop_scope(self) -> SemanticScope:
        return self.scope_stack.pop()

    def _current_scope(self) -> SemanticScope:
        return self.scope_stack[-1]

    def _error(self, message: str, line: int = 0) -> None:
        self.errors.append(f"Semantic error at line {line}: {message}")

    def _warning(self, message: str, line: int = 0) -> None:
        self.warnings.append(f"Semantic warning at line {line}: {message}")

    def analyze(self, program: object) -> object:
        from ir import IRModule, IRImport, IRFunction, IRClass, IRVariable, IRType, IRBasicBlock
        from ko_compiler import FuncDecl, ClassDecl, VarDecl, Assignment, NowMutation
        from ko_compiler import IfStmt, ForLoop, WhileLoop, Call, ImportStmt, CatchStmt

        self.scope_stack = []
        self._push_scope("global")

        ir_module = IRModule()

        for imp in program.imports:
            if imp.module_name not in self.ALLOWED_MODULES:
                self._error(f"Disallowed module '{imp.module_name}'", 0)
            else:
                ir_module.imports.append(IRImport(imp.module_name, imp.alias, imp.scope_tag))
                self._current_scope().define_import(imp.alias, imp.module_name)

        for decl in program.decls:
            if isinstance(decl, FuncDecl):
                if decl.name in self._current_scope().functions:
                    self._error(f"Duplicate function declaration '{decl.name}'", 0)
                self._current_scope().define_func(decl.name, decl)
            elif isinstance(decl, ClassDecl):
                if decl.name in self._current_scope().classes:
                    self._error(f"Duplicate class declaration '{decl.name}'", 0)
                self._current_scope().define_class(decl.name, decl)

        for decl in program.decls:
            if isinstance(decl, FuncDecl):
                self._analyze_function(decl, ir_module)
            elif isinstance(decl, ClassDecl):
                self._analyze_class(decl, ir_module)

        if program.main is not None:
            self._analyze_main(program.main, ir_module)

        for catch in program.catch_blocks:
            self._analyze_catch(catch, ir_module)

        self._validate_global_scope(program)

        if self.errors:
            from ko_compiler import KoCompileError
            raise KoCompileError(
                f"Semantic analysis failed with {len(self.errors)} error(s): "
                + "; ".join(self.errors[:5])
            )

        return ir_module

    def _analyze_function(self, func: object, ir_module: IRModule) -> None:
        from ir import IRFunction, IRVariable, IRType

        for param in func.params:
            ir_var = IRVariable(param.name, self._type_name_to_ir_type(param.type_name), defined=True)
            ir_module.global_vars[param.name] = ir_var

        func_ir = IRFunction(
            name=func.name,
            params=[IRVariable(p.name, self._type_name_to_ir_type(p.type_name), defined=True) for p in func.params],
            body=[],
            return_type=IRType.UNKNOWN,
            local_vars={}
        )

        old_function = self.current_function
        old_return_count = self.return_count
        old_func_return_type = self.function_return_type
        self.current_function = func.name
        self.return_count = 0
        self.function_return_type = None

        scope = self._push_scope(func.name)
        for param in func.params:
            scope.define_var(param.name, param.type_name or "unknown")

        for stmt in func.body:
            self._analyze_statement(stmt, scope, ir_module)

        func_ir.return_type = self._type_str_to_ir(self.function_return_type) if self.function_return_type else IRType.UNKNOWN
        self._pop_scope()

        self.current_function = old_function
        self.return_count = old_return_count
        self.function_return_type = old_func_return_type

        ir_module.functions[func.name] = func_ir

    def _analyze_class(self, cls: object, ir_module: IRModule) -> None:
        from ir import IRClass, IRVariable, IRType, IRFunction
        from ko_compiler import VarDecl, FuncDecl

        fields: Dict[str, IRVariable] = {}
        methods: Dict[str, IRFunction] = {}
        private_fields: Dict[str, IRVariable] = {}
        private_methods: Dict[str, IRFunction] = {}

        old_class = self.current_class
        self.current_class = cls.name

        for stmt in cls.body:
            if isinstance(stmt, VarDecl):
                var_type = stmt.type_name or "unknown"
                fields[stmt.name] = IRVariable(stmt.name, self._type_name_to_ir_type(var_type), defined=True)
            elif isinstance(stmt, FuncDecl):
                methods[stmt.name] = self._build_method_ir(stmt)

        for stmt in cls.private_body:
            if isinstance(stmt, VarDecl):
                var_type = stmt.type_name or "unknown"
                private_fields[stmt.name] = IRVariable(stmt.name, self._type_name_to_ir_type(var_type), defined=True)
            elif isinstance(stmt, FuncDecl):
                private_methods[stmt.name] = self._build_method_ir(stmt)

        ir_class = IRClass(
            name=cls.name,
            fields=fields,
            methods=methods,
            private_fields=private_fields,
            private_methods=private_methods
        )
        ir_module.classes[cls.name] = ir_class
        self.current_class = old_class

    def _build_method_ir(self, func: object) -> IRFunction:
        from ir import IRFunction, IRVariable, IRType
        return IRFunction(
            name=func.name,
            params=[IRVariable(p.name, self._type_name_to_ir_type(p.type_name), defined=True) for p in func.params],
            body=[],
            return_type=IRType.UNKNOWN,
            is_method=True,
            is_private=False
        )

    def _analyze_main(self, main: object, ir_module: IRModule) -> None:
        from ir import IRBasicBlock

        scope = self._push_scope("main")
        bb = IRBasicBlock("main_entry")
        ir_module.main = [bb]

        old_function = self.current_function
        self.current_function = "__main__"
        self._current_scope().define_var("__main__", "main")

        for stmt in main.body:
            self._analyze_statement(stmt, scope, ir_module)

        self.current_function = old_function
        self._pop_scope()

    def _analyze_catch(self, catch: object, ir_module: IRModule) -> None:
        from ir import IRCatchBlock, IRBasicBlock

        body_blocks: List[IRBasicBlock] = []
        scope = self._push_scope("catch")
        scope.define_var("error", "dict")

        for stmt in catch.body:
            bb = IRBasicBlock(f"catch_body_{len(body_blocks)}")
            body_blocks.append(bb)
            self._analyze_statement(stmt, scope, ir_module)

        self._pop_scope()
        ir_module.catch_blocks.append(IRCatchBlock(
            error_code=catch.error_condition if isinstance(catch.error_condition, str) else None,
            condition=str(catch.error_condition) if not isinstance(catch.error_condition, str) else None,
            body=body_blocks
        ))

    def _analyze_statement(self, stmt: object, scope: SemanticScope, ir_module: IRModule) -> None:
        from ko_compiler import VarDecl, Assignment, NowMutation, IfStmt, ForLoop, WhileLoop
        from ko_compiler import Call, FuncDecl, ClassDecl, ImportStmt, CatchStmt

        if isinstance(stmt, VarDecl):
            self._analyze_var_decl(stmt, scope, ir_module)
        elif isinstance(stmt, Assignment):
            self._analyze_assignment(stmt, scope, ir_module)
        elif isinstance(stmt, NowMutation):
            self._analyze_now_mutation(stmt, scope, ir_module)
        elif isinstance(stmt, IfStmt):
            self._analyze_if(stmt, scope, ir_module)
        elif isinstance(stmt, ForLoop):
            self._analyze_for_loop(stmt, scope, ir_module)
        elif isinstance(stmt, WhileLoop):
            self._analyze_while_loop(stmt, scope, ir_module)
        elif isinstance(stmt, FuncDecl):
            self._analyze_function(stmt, ir_module)
        elif isinstance(stmt, ClassDecl):
            self._analyze_class(stmt, ir_module)
        elif isinstance(stmt, Call):
            self._analyze_call(stmt, scope, ir_module)
        elif isinstance(stmt, CatchStmt):
            self._analyze_catch(stmt, ir_module)

    def _analyze_var_decl(self, stmt: VarDecl, scope: SemanticScope, ir_module: IRModule) -> None:
        from ir import IRVariable
        if stmt.name in scope.variables:
            self._warning(f"Variable '{stmt.name}' shadows a previous declaration", 0)

        if stmt.initializer is not None:
            self._analyze_expression(stmt.initializer, scope, ir_module)

        var_type = stmt.type_name or "unknown"
        scope.define_var(stmt.name, var_type)
        ir_var = IRVariable(stmt.name, self._type_name_to_ir_type(var_type), defined=True)
        ir_module.global_vars[stmt.name] = ir_var

    def _analyze_assignment(self, stmt: Assignment, scope: SemanticScope, ir_module: IRModule) -> None:
        self._analyze_expression(stmt.value, scope, ir_module)

        var_type = scope.lookup_var(stmt.target.name)
        if var_type is None:
            self._warning(f"Assignment to undeclared variable '{stmt.target.name}'", 0)
        elif stmt.type_name and var_type != stmt.type_name:
            self._warning(f"Type mismatch in assignment to '{stmt.target.name}': expected {var_type}, got {stmt.type_name}", 0)

    def _analyze_now_mutation(self, stmt: NowMutation, scope: SemanticScope, ir_module: IRModule) -> None:
        self._analyze_expression(stmt.expr, scope, ir_module)
        var_type = scope.lookup_var(stmt.target.name)
        if var_type is None:
            self._warning(f"Mutation of undeclared variable '{stmt.target.name}'", 0)

    def _analyze_if(self, stmt: IfStmt, scope: SemanticScope, ir_module: IRModule) -> None:
        self._analyze_expression(stmt.condition, scope, ir_module)
        self._analyze_statement_block(stmt.body, scope, ir_module)
        if stmt.else_body:
            if isinstance(stmt.else_body, IfStmt):
                self._analyze_if(stmt.else_body, scope, ir_module)
            else:
                self._analyze_statement_block(stmt.else_body, scope, ir_module)

    def _analyze_for_loop(self, stmt: ForLoop, scope: SemanticScope, ir_module: IRModule) -> None:
        old_loop = self.loop_depth
        self.loop_depth += 1

        self._analyze_expression(stmt.start, scope, ir_module)
        self._analyze_expression(stmt.end, scope, ir_module)
        if stmt.step:
            self._analyze_expression(stmt.step, scope, ir_module)

        scope.define_var(stmt.var_name, "int")
        self._analyze_statement_block(stmt.body, scope, ir_module)

        self.loop_depth = old_loop

    def _analyze_while_loop(self, stmt: WhileLoop, scope: SemanticScope, ir_module: IRModule) -> None:
        old_loop = self.loop_depth
        self.loop_depth += 1

        self._analyze_expression(stmt.condition, scope, ir_module)
        self._analyze_statement_block(stmt.body, scope, ir_module)

        self.loop_depth = old_loop

    def _analyze_call(self, stmt: Call, scope: SemanticScope, ir_module: IRModule) -> None:
        for arg in stmt.args:
            self._analyze_expression(arg, scope, ir_module)

    def _analyze_expression(self, expr: object, scope: SemanticScope, ir_module: IRModule) -> None:
        from ko_compiler import Literal, Identifier, BinaryOp, UnaryOp, Call, Indexing, TupleLiteral, DictLiteral

        if isinstance(expr, Identifier):
            var_type = scope.lookup_var(expr.name)
            if var_type is None:
                self._error(f"Undefined variable '{expr.name}'", 0)
        elif isinstance(expr, BinaryOp):
            self._analyze_expression(expr.left, scope, ir_module)
            self._analyze_expression(expr.right, scope, ir_module)
            self._check_type_compatibility(expr.left, expr.right, expr.op)
        elif isinstance(expr, UnaryOp):
            self._analyze_expression(expr.expr, scope, ir_module)
        elif isinstance(expr, Call):
            self._analyze_call(expr, scope, ir_module)
            for arg in expr.args:
                self._analyze_expression(arg, scope, ir_module)
            func_decl = scope.lookup_func(expr.name)
            if func_decl is None and self.current_class is None:
                cls = scope.lookup_class(expr.name)
                if cls is None:
                    self._warning(f"Call to undefined function '{expr.name}'", 0)
        elif isinstance(expr, Indexing):
            self._analyze_expression(expr.target, scope, ir_module)
            for idx in expr.index:
                self._analyze_expression(idx, scope, ir_module)
        elif isinstance(expr, TupleLiteral):
            for elem in expr.elements:
                self._analyze_expression(elem, scope, ir_module)
        elif isinstance(expr, DictLiteral):
            for k, v in expr.mapping.items():
                self._analyze_expression(k, scope, ir_module)
                self._analyze_expression(v, scope, ir_module)

    def _analyze_statement_block(self, stmts, scope: SemanticScope, ir_module: IRModule) -> None:
        for stmt in stmts:
            self._analyze_statement(stmt, scope, ir_module)

    def _check_type_compatibility(self, left: object, right: object, op) -> None:
        from ko_compiler import TokenType
        if op in (TokenType.AND, TokenType.OR):
            return
        if op in (TokenType.EQ, TokenType.NE, TokenType.GT, TokenType.GE, TokenType.LE, TokenType.LANGLE):
            return

    def _type_name_to_ir_type(self, type_name: Optional[str]) -> object:
        from ir import IRType
        if type_name is None:
            return IRType.UNKNOWN
        mapping = {
            "int": IRType.INT,
            "freal": IRType.FREAL,
            "string": IRType.STRING,
            "booling": IRType.BOOL,
            "byte": IRType.BYTE,
            "bytes": IRType.BYTES,
        }
        return mapping.get(type_name, IRType.UNKNOWN)

    def _type_str_to_ir(self, type_str: Optional[str]) -> object:
        from ir import IRType
        if type_str is None:
            return IRType.UNKNOWN
        return self._type_name_to_ir_type(type_str)

    def _validate_global_scope(self, program: object) -> None:
        from ko_compiler import VarDecl, Call

        for catch in program.catch_blocks:
            if isinstance(catch.error_condition, str):
                if not catch.error_condition.startswith("`") or not catch.error_condition.endswith("`"):
                    self._warning(f"Error code '{catch.error_condition}' should be wrapped in backticks", 0)

    def get_errors(self) -> List[str]:
        return self.errors

    def get_warnings(self) -> List[str]:
        return self.warnings

    def has_errors(self) -> bool:
        return len(self.errors) > 0