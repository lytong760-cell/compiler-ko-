from __future__ import annotations

import argparse
import ast
import enum
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

class KoCompileError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(f"{message} at line {line}, column {column}")
        self.message = message
        self.line = line
        self.column = column


class TokenType(enum.Enum):
    # Literals
    INT = "INT"
    FREAL = "FREAL"
    STRING = "STRING"
    BOOL = "BOOL"
    BYTE = "BYTE"
    ID = "ID"

    # Keywords
    IMPORT = "Import"
    LOOP = "Loop"
    CLASS = "!class"
    PRIVATE = "@private"
    LOOP_CTRL = "@loop"
    ALSO = "@also"
    IF = "<if>"
    ELIF = "<elif>"
    ELSE = "<else>"
    RETURN = "<return>"
    CATCH = "<catch>"
    MEMORY = "<memory>"
    NOW = "<now>"
    PRINT = "<print>"
    PRINTF = "<printf>"
    INPUT = "<input>"
    FOR = "<for>"
    WHILE_ALSO = "<for.f.whle>@also"
    ENCODE = "<encode("
    LEN = "<len>"

    # Sigils & Delimiters
    TILDE = "~"
    DOLLAR = "$"
    LBRACKET = "["
    RBRACKET = "]"
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LANGLE = "<"
    RANGLE = ">"
    COMMA = ","
    BACKTICK = "`"
    COLON = ":"
    CARET = "^"
    BANG = "!"

    # Operators
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    PERCENT = "%"
    AND = "&&"
    OR = "%%"
    ASSIGN_INPUT = "&="
    ASSIGN = "="
    GT = ">"
    EQ = "=="
    NE = "!="
    GE = ">="
    LE = "<="

    EOF = "EOF"


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int


class KoLexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
        self.quote_stack = []  # Stack of (quote_char, brace_depth) tuples

    def _error(self, message: str):
        raise KoCompileError(message, self.line, self.column)

    def _peek(self, offset: int = 0) -> str:
        if self.pos + offset >= len(self.source):
            return ""
        return self.source[self.pos + offset]

    def _advance(self) -> str:
        char = self._peek()
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            char = self._peek()

            if char.isspace():
                self._advance()
                continue
            
            # Multi-char operators first
            if char == "&" and self._peek(1) == "&":
                self.tokens.append(Token(TokenType.AND, "&&", self.line, self.column))
                self._advance(); self._advance()
                continue
            if char == "%" and self._peek(1) == "%":
                self.tokens.append(Token(TokenType.OR, "%%", self.line, self.column))
                self._advance(); self._advance()
                continue
            if char == "&" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.ASSIGN_INPUT, "&=", self.line, self.column))
                self._advance(); self._advance()
                continue
            if char == "=" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.EQ, "==", self.line, self.column))
                self._advance(); self._advance()
                continue
            if char == "!" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.NE, "!=", self.line, self.column))
                self._advance(); self._advance()
                continue
            if char == ">" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.GE, ">=", self.line, self.column))
                self._advance(); self._advance()
                continue
            if char == "<" and self._peek(1) == "=":
                self.tokens.append(Token(TokenType.LE, "<=", self.line, self.column))
                self._advance(); self._advance()
                continue
            
            if self.quote_stack and char == "{":
                self.quote_stack[-1] = (self.quote_stack[-1][0], self.quote_stack[-1][1] + 1)
                self.tokens.append(Token(TokenType.LBRACE, "{", self.line, self.column))
                self._advance()
                continue

            if self.quote_stack and char == "}":
                if self.quote_stack[-1][1] > 1:
                    self.quote_stack[-1] = (self.quote_stack[-1][0], self.quote_stack[-1][1] - 1)
                    self.tokens.append(Token(TokenType.RBRACE, "}", self.line, self.column))
                    self._advance()
                else:
                    self.tokens.append(Token(TokenType.RBRACE, "}", self.line, self.column))
                    self._advance()
                    self._tokenize_string_fragment(self.quote_stack.pop()[0], continuation=True)
                continue

            if char == "|":
                self._advance()
                while self._peek() and self._peek() != "|":
                    self._advance()
                if self._peek() == "|":
                    self._advance()
                continue

            # Special Tags and Keywords
            if char == "<":
                text = ""
                start_col = self.column
                # Check for <encode( which contains a parenthesis
                if self._peek(1) == "e" and self._peek(2) == "n" and self._peek(3) == "c" and self._peek(4) == "o" and self._peek(5) == "d" and self._peek(6) == "e" and self._peek(7) == "(":
                    for _ in range(8): text += self._advance()
                    self.tokens.append(Token(TokenType.ENCODE, text, self.line, start_col))
                    continue
                # Peak ahead to see if it's a known tag
                temp_pos = self.pos
                temp_text = ""
                while temp_pos < len(self.source) and not self.source[temp_pos].isspace() and self.source[temp_pos] not in "()^":
                    temp_text += self.source[temp_pos]
                    temp_pos += 1
                    if self.source[temp_pos-1] == ">":
                        # Check for @also suffix on compound tokens like <for.f.whle>@also
                        remaining = self.source[temp_pos:].lstrip()
                        if remaining.startswith("@also"):
                            temp_text += "@also"
                            temp_pos += len("@also")
                        break
                
                tag_map = {
                    "<if>": TokenType.IF,
                    "<elif>": TokenType.ELIF,
                    "<else>": TokenType.ELSE,
                    "<return>": TokenType.RETURN,
                    "<catch>": TokenType.CATCH,
                    "<memory>": TokenType.MEMORY,
                    "<now>": TokenType.NOW,
                    "<print>": TokenType.PRINT,
                    "<printf>": TokenType.PRINTF,
                    "<input>": TokenType.INPUT,
                    "<for>": TokenType.FOR,
                    "<for.f.whle>@also": TokenType.WHILE_ALSO,
                    "<encode(": TokenType.ENCODE,
                    "<len>": TokenType.LEN,
                }
                
                if temp_text in tag_map:
                    for _ in range(len(temp_text)): self._advance()
                    self.tokens.append(Token(tag_map[temp_text], temp_text, self.line, start_col))
                    continue
                
                self.tokens.append(Token(TokenType.LANGLE, "<", self.line, start_col))
                self._advance()
                continue

            if char == "\\":
                start_col = self.column
                self._advance()
                text = ""
                while self._peek() and self._peek() != "\\":
                    text += self._advance()
                if self._peek() == "\\":
                    self._advance()
                    if text == "True":
                        self.tokens.append(Token(TokenType.BOOL, True, self.line, start_col))
                    elif text == "False":
                        self.tokens.append(Token(TokenType.BOOL, False, self.line, start_col))
                    else:
                        self._error(f"Invalid boolean literal: \\{text}\\")
                    continue
                else:
                    self._error("Unterminated boolean literal")

            if char.isdigit():
                start_col = self.column
                num_str = ""
                while self._peek().isdigit() or self._peek() == ".":
                    num_str += self._advance()
                if "." in num_str:
                    self.tokens.append(Token(TokenType.FREAL, float(num_str), self.line, start_col))
                else:
                    self.tokens.append(Token(TokenType.INT, int(num_str), self.line, start_col))
                continue

            if char.isalpha() or char == "_" or char == "@" or char == "!" or (char == "*" and self._peek(1) == "*"):
                start_col = self.column
                text = ""
                if char == "*" and self._peek(1) == "*":
                    for _ in range(2): text += self._advance()
                    while self._peek().isalpha(): text += self._advance()
                    if self._peek() == "*" and self._peek(1) == "*":
                        for _ in range(2): text += self._advance()
                elif char == "!":
                    text += self._advance()
                    while self._peek().isalpha(): text += self._advance()
                # Keep IDs together if they contain sigils in the middle (like @app_server)
                while self._peek().isalnum() or self._peek() in "_@":
                    text += self._advance()
                
                kw_map = {
                    "!class": TokenType.CLASS,
                    "@private": TokenType.PRIVATE,
                    "@loop": TokenType.LOOP_CTRL,
                    "@also": TokenType.ALSO,
                    "int": TokenType.ID,
                    "freal": TokenType.ID,
                    "string": TokenType.ID,
                    "booling": TokenType.ID,
                    "byte": TokenType.ID,
                    "bytes": TokenType.ID,
                    "!": TokenType.BANG,
                }
                
                if text == "**Loop**":
                    self.tokens.append(Token(TokenType.LOOP, text, self.line, start_col))
                elif text == "**Import**":
                    self.tokens.append(Token(TokenType.IMPORT, text, self.line, start_col))
                elif text in kw_map:
                    self.tokens.append(Token(kw_map[text], text, self.line, start_col))
                else:
                    self.tokens.append(Token(TokenType.ID, text, self.line, start_col))
                continue

            if char in "\"'":
                self._tokenize_string_fragment(self._advance())
                continue

            if char == "*":
                self.tokens.append(Token(TokenType.STAR, "*", self.line, self.column))
                self._advance()
                continue
            if char in "~":
                self.tokens.append(Token(TokenType.TILDE, char, self.line, self.column))
                self._advance()
                continue
            char_map = {
                "$": TokenType.DOLLAR,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                ">": TokenType.RANGLE,
                ",": TokenType.COMMA,
                "`": TokenType.BACKTICK,
                ":": TokenType.COLON,
                "^": TokenType.CARET,
                "!": TokenType.BANG,
                "=": TokenType.ASSIGN,
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "/": TokenType.SLASH,
                "%": TokenType.PERCENT,
            }
            
            if char in char_map:
                self.tokens.append(Token(char_map[char], char, self.line, self.column))
                self._advance()
                continue

            self._error(f"Unexpected character: {char}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens

    def _tokenize_string_fragment(self, quote: str, continuation: bool = False):
        start_col = self.column
        content = ""
        brace_depth = 0
        while self._peek() and self._peek() != quote:
            if self._peek() == "{" and brace_depth == 0:
                if content:
                    self.tokens.append(Token(TokenType.STRING, content, self.line, start_col))
                self.tokens.append(Token(TokenType.LBRACE, "{", self.line, self.column))
                self._advance()
                self.quote_stack.append((quote, 1))
                return
            elif self._peek() == "{":
                brace_depth += 1
                content += self._advance()
            elif self._peek() == "}" and brace_depth == 0:
                if continuation:
                    if content:
                        self.tokens.append(Token(TokenType.STRING, content, self.line, start_col))
                    self.tokens.append(Token(TokenType.RBRACE, "}", self.line, self.column))
                    self._advance()
                    start_col = self.column
                    continue
                else:
                    content += self._advance()
            elif self._peek() == "}" and brace_depth > 0:
                brace_depth -= 1
                content += self._advance()
            elif self._peek() == ">" and brace_depth == 0:
                content += self._advance()
            elif self._peek() == "\\":
                self._advance()
                next_char = self._advance()
                if next_char == "n":
                    content += "\n"
                elif next_char == "t":
                    content += "\t"
                elif next_char == "r":
                    content += "\r"
                elif next_char == "\\":
                    content += "\\"
                elif next_char == '"':
                    content += '"'
                else:
                    content += "\\" + next_char
            else:
                content += self._advance()

        if self._peek() == quote:
            self._advance()
            self.tokens.append(Token(TokenType.STRING, content, self.line, start_col))
        else:
            self._error("Unterminated string literal")


# AST Nodes
class Node:
    pass

class Expr(Node):
    pass

@dataclass(frozen=True)
class Literal(Expr):
    value: Any

@dataclass
class Identifier(Expr):
    name: str

@dataclass
class BinaryOp(Expr):
    left: Expr
    op: TokenType
    right: Expr

@dataclass
class UnaryOp(Expr):
    op: TokenType
    expr: Expr

@dataclass
class Indexing(Expr):
    target: Expr
    index: List[Expr]

@dataclass
class Call(Expr):
    name: str
    args: List[Expr]
    is_instance_method: bool = False
    instance: Optional[str] = None
    target: Optional[str] = None

@dataclass
class TupleLiteral(Expr):
    elements: List[Expr]

@dataclass
class DictLiteral(Expr):
    mapping: Dict[Expr, Expr]

class Stmt(Node):
    pass

@dataclass
class VarDecl(Stmt):
    type_name: str
    initializer: Expr
    name: str
    is_instantiation: bool = False

@dataclass
class Assignment(Stmt):
    target: Identifier
    value: Expr
    type_name: Optional[str] = None

@dataclass
class NowMutation(Stmt):
    expr: Expr
    target: Identifier

@dataclass
class IfStmt(Stmt):
    condition: Expr
    body: List[Stmt]
    else_body: Optional[List[Stmt] | IfStmt] = None

@dataclass
class ForLoop(Stmt):
    var_name: str
    start: Expr
    end: Expr
    body: List[Stmt]
    step: Optional[Expr] = None

@dataclass
class WhileLoop(Stmt):
    condition: Expr
    body: List[Stmt]

@dataclass
class FuncDecl(Stmt):
    name: str
    params: List[VarDecl]
    body: List[Stmt]

@dataclass
class ClassDecl(Stmt):
    name: str
    body: List[Stmt]
    private_body: List[Stmt] = field(default_factory=list)

@dataclass
class ImportStmt(Stmt):
    module_name: str
    alias: str
    scope_tag: str

@dataclass
class CatchStmt(Stmt):
    error_condition: Union[str, Expr] # ErrorCode in backticks or Expr
    body: List[Stmt]

@dataclass
class MainBlock(Stmt):
    body: List[Stmt]

@dataclass
class Program(Node):
    imports: List[ImportStmt]
    decls: List[Union[FuncDecl, ClassDecl]]
    main: Optional[MainBlock]
    catch_blocks: List[CatchStmt]


class KoParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self._dict_literal_depth = 0

    def _error(self, message: str):
        token = self._peek()
        raise KoCompileError(message, token.line, token.column)

    def _peek(self, offset: int = 0) -> Token:
        if self.pos + offset >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.pos + offset]

    def _advance(self) -> Token:
        token = self._peek()
        self.pos += 1
        return token

    def _check(self, type: TokenType) -> bool:
        return self._peek().type == type

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, type: TokenType, message: str) -> Token:
        if self._check(type):
            return self._advance()
        self._error(message)

    def parse(self) -> Program:
        imports = []
        decls = []
        main = None
        catch_blocks = []

        while not self._check(TokenType.EOF):
            if self._check(TokenType.IMPORT):
                imports.append(self.parse_import())
            elif self._check(TokenType.ID) and self._peek(1).type == TokenType.CLASS:
                decls.append(self.parse_class())
            elif self._check(TokenType.ID) and self._peek(1).type == TokenType.LPAREN:
                decls.append(self.parse_function())
            elif self._check(TokenType.ID) and self._peek(1).type == TokenType.LBRACKET:
                decls.append(self.parse_function()) # Function with no params
            elif self._check(TokenType.LBRACKET):
                if main is not None:
                    self._error("Multiple main blocks found")
                main = self.parse_main_block()
            elif self._check(TokenType.CATCH):
                catch_blocks.append(self.parse_catch())
            elif self._check(TokenType.LPAREN):
                decls.append(self.parse_tuple_decl())
            elif self._check(TokenType.LBRACE):
                decls.append(self.parse_dict_decl())
            else:
                token = self._peek()
                self._error(f"Global scope execution constraint violation: unexpected statement '{token.value}' at top level")

        return Program(imports, decls, main, catch_blocks)

    def parse_import(self) -> ImportStmt:
        self._consume(TokenType.IMPORT, "Expected Import")
        self._consume(TokenType.LPAREN, "Expected (")
        self._consume(TokenType.DOLLAR, "Expected $")
        module_name = self._consume(TokenType.ID, "Expected module name").value
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.ALSO, "Expected @also")
        self._consume(TokenType.PERCENT, "Expected %")
        self._consume(TokenType.TILDE, "Expected ~")
        alias = self._consume(TokenType.ID, "Expected alias").value
        self._consume(TokenType.BANG, "Expected !")
        self._consume(TokenType.BACKTICK, "Expected `")
        scope_tag = self._consume(TokenType.ID, "Expected scope tag").value
        self._consume(TokenType.BACKTICK, "Expected `")
        self._consume(TokenType.COLON, "Expected :")
        self._consume(TokenType.ID, "Expected final alias")
        return ImportStmt(module_name, alias, scope_tag)

    def parse_class(self) -> ClassDecl:
        name = self._consume(TokenType.ID, "Expected class name").value
        self._consume(TokenType.CLASS, "Expected !class")
        self._consume(TokenType.LBRACKET, "Expected [")
        
        body = []
        private_body = []
        while not self._check(TokenType.RBRACKET) and not self._check(TokenType.EOF):
            if self._check(TokenType.PRIVATE):
                private_body.extend(self.parse_private_block())
            else:
                body.append(self.parse_statement())
        
        self._consume(TokenType.RBRACKET, "Expected ]")
        return ClassDecl(name, body, private_body)

    def parse_private_block(self) -> List[Stmt]:
        self._consume(TokenType.PRIVATE, "Expected @private")
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET) and not self._check(TokenType.EOF):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        return body

    def parse_function(self) -> FuncDecl:
        name = self._consume(TokenType.ID, "Expected function name").value
        params = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                while True:
                    params.append(self.parse_var_decl_param())
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RPAREN, "Expected )")
        
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET) and not self._check(TokenType.EOF):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        return FuncDecl(name, params, body)

    def parse_var_decl_param(self) -> VarDecl:
        type_name = self._consume(TokenType.ID, "Expected type").value
        self._consume(TokenType.TILDE, "Expected ~")
        name = self._consume(TokenType.ID, "Expected param name").value
        return VarDecl(type_name, None, name)

    def parse_main_block(self) -> MainBlock:
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET) and not self._check(TokenType.EOF):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        return MainBlock(body)

    def parse_catch(self) -> CatchStmt:
        self._consume(TokenType.CATCH, "Expected <catch>")
        self._consume(TokenType.LPAREN, "Expected (")
        
        if self._match(TokenType.BACKTICK):
            error_code = self._consume(TokenType.ID, "Expected error code").value
            self._consume(TokenType.BACKTICK, "Expected `")
            self._consume(TokenType.RPAREN, "Expected )")
            condition = f"`{error_code}`"
        else:
            condition = self.parse_expression(stop_tokens=[TokenType.RPAREN])
            self._consume(TokenType.RPAREN, "Expected )")
        
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET) and not self._check(TokenType.EOF):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        return CatchStmt(condition, body)

    def parse_statement(self) -> Stmt:
        if self._check(TokenType.IF):
            return self.parse_if()
        elif self._check(TokenType.CATCH):
            return self.parse_catch()
        elif self._check(TokenType.LOOP_CTRL):
            return self.parse_while()
        elif self._check(TokenType.LOOP):
            return self.parse_for()
        elif self._check(TokenType.NOW):
            return self.parse_now()
        elif self._check(TokenType.MEMORY):
            return self.parse_memory()
        elif self._check(TokenType.PRINT) or self._check(TokenType.PRINTF):
            return self.parse_print()
        elif self._check(TokenType.INPUT):
            return self.parse_input()
        elif self._check(TokenType.RETURN):
            return self.parse_return()
        elif self._check(TokenType.TILDE):
            return self.parse_call_or_instantiation()
        elif self._check(TokenType.DOLLAR):
            return self.parse_call_or_instantiation()
        elif self._check(TokenType.LANGLE):
            return self.parse_system_tag_statement()
        elif self._check(TokenType.ENCODE):
            return self.parse_encode()
        elif self._check(TokenType.LEN):
            return self.parse_len()
        elif self._check(TokenType.LPAREN):
            return self.parse_tuple_decl()
        elif self._check(TokenType.LBRACE):
            return self.parse_dict_decl()
        elif self._check(TokenType.ID):
            if self._peek(1).type == TokenType.LPAREN:
                return self._parse_id_lparen_statement()
            elif self._peek(1).type == TokenType.LBRACKET:
                return self.parse_function()
        
        self._error(f"Unexpected statement: {self._peek().type}")

    def parse_system_tag_statement(self) -> Stmt:
        # Handle system tag calls at statement level: <$module>(args)[~var|@target]
        self._consume(TokenType.LANGLE, "Expected <")
        self._consume(TokenType.DOLLAR, "Expected $")
        module_name = self._consume(TokenType.ID, "Expected module name").value
        self._consume(TokenType.RANGLE, "Expected >")

        func_name = None
        if self._check(TokenType.ID):
            func_name = self._advance().value

        self._match(TokenType.CARET)  # Consume ^ if present

        args = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                while True:
                    args.append(self.parse_expression(stop_tokens=[TokenType.RPAREN, TokenType.COMMA]))
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RPAREN, "Expected )")

        full_name = f"{module_name}.{func_name}" if func_name else module_name

        # Check for ~var (assignment) or @target (target assignment)
        if self._match(TokenType.TILDE):
            var_name = self._consume(TokenType.ID, "Expected variable name").value
            return Assignment(Identifier(var_name), Call(full_name, args))
        elif self._check(TokenType.ID) and self._peek().value.startswith("@"):
            target = self._advance().value[1:]
            return Call(full_name, args, target=target)

        # Just a call expression as statement
        return Call(full_name, args)

    def parse_encode(self) -> Stmt:
        self._consume(TokenType.ENCODE, "Expected <encode(")
        self._consume(TokenType.BACKTICK, "Expected `")
        encoding_parts = []
        while not self._check(TokenType.BACKTICK) and not self._check(TokenType.RPAREN) and not self._check(TokenType.EOF):
            encoding_parts.append(self._advance().value)
        encoding_type = "".join(str(p) for p in encoding_parts)
        self._consume(TokenType.BACKTICK, "Expected `")
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.GT, "Expected >")
        self._consume(TokenType.CARET, "Expected ^")
        self._consume(TokenType.LPAREN, "Expected (")
        expr = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        return Call("encode", [expr, Literal(encoding_type)])

    def parse_len(self) -> Expr:
        self._consume(TokenType.LEN, "Expected <len>")
        self._match(TokenType.CARET)
        self._consume(TokenType.LPAREN, "Expected (")
        expr = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        return Call("len", [expr])

    def parse_tuple_decl(self) -> VarDecl:
        # Handle tuple/array declarations at statement level: (expr, expr)~name
        self._consume(TokenType.LPAREN, "Expected (")
        elements = []
        if not self._check(TokenType.RPAREN):
            while True:
                elements.append(self.parse_expression(stop_tokens=[TokenType.RPAREN, TokenType.COMMA]))
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.TILDE, "Expected ~")
        name = self._consume(TokenType.ID, "Expected variable name").value
        # Build a TupleLiteral as the initializer
        initializer = TupleLiteral(elements) if len(elements) > 1 else elements[0] if elements else Literal(None)
        return VarDecl("", initializer, name)

    def parse_dict_decl(self) -> VarDecl:
        # Handle dict declarations at statement level: {key: value}~name
        self._consume(TokenType.LBRACE, "Expected {")
        mapping = {}
        if not self._check(TokenType.RBRACE):
            key = self.parse_expression(stop_tokens=[TokenType.COLON, TokenType.RBRACE])
            self._consume(TokenType.COLON, "Expected :")
            value = self.parse_expression(stop_tokens=[TokenType.RBRACE])
            mapping[key] = value
            while self._match(TokenType.COMMA):
                key = self.parse_expression(stop_tokens=[TokenType.COLON, TokenType.RBRACE])
                self._consume(TokenType.COLON, "Expected :")
                value = self.parse_expression(stop_tokens=[TokenType.RBRACE])
                mapping[key] = value
        self._consume(TokenType.RBRACE, "Expected }")
        self._consume(TokenType.TILDE, "Expected ~")
        name = self._consume(TokenType.ID, "Expected variable name").value
        return VarDecl("", DictLiteral(mapping), name)

    def _parse_id_lparen_statement(self) -> Stmt:
        # Check if it's a function decl or var decl
        # ID(expr)~name is var decl
        # ID(...) [ is function decl
        temp_pos = self.pos + 2
        nesting = 1
        is_func = False
        while temp_pos < len(self.tokens):
            t = self.tokens[temp_pos]
            if t.type == TokenType.LPAREN: nesting += 1
            elif t.type == TokenType.RPAREN:
                nesting -= 1
                if nesting == 0:
                    if self._peek(temp_pos - self.pos + 1).type == TokenType.LBRACKET:
                        is_func = True
                    break
            temp_pos += 1
        if is_func:
            return self.parse_function()
        else:
            return self.parse_var_decl()

    def parse_var_decl(self) -> VarDecl:
        type_name = self._consume(TokenType.ID, "Expected type name").value
        self._consume(TokenType.LPAREN, "Expected (")
        initializer = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.TILDE, "Expected ~")
        name = self._consume(TokenType.ID, "Expected variable name").value
        return VarDecl(type_name, initializer, name)

    def parse_if(self) -> IfStmt:
        self._consume(TokenType.IF, "Expected <if>")
        self._consume(TokenType.LPAREN, "Expected (")
        condition = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        
        else_body = None
        if self._check(TokenType.ELIF):
            else_body = self.parse_elif()
        elif self._check(TokenType.ELSE):
            else_body = self.parse_else()
        
        return IfStmt(condition, body, else_body)

    def parse_elif(self) -> IfStmt:
        self._consume(TokenType.ELIF, "Expected <elif>")
        self._consume(TokenType.LPAREN, "Expected (")
        condition = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        
        else_body = None
        if self._check(TokenType.ELIF):
            else_body = self.parse_elif()
        elif self._check(TokenType.ELSE):
            else_body = self.parse_else()
        
        return IfStmt(condition, body, else_body)

    def parse_else(self) -> List[Stmt]:
        self._consume(TokenType.ELSE, "Expected <else>")
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        return body

    def parse_for(self) -> ForLoop:
        self._consume(TokenType.LOOP, "Expected **Loop**")
        self._consume(TokenType.FOR, "Expected <for>")
        self._consume(TokenType.LPAREN, "Expected (")
        self._consume(TokenType.TILDE, "Expected ~")
        var_name = self._consume(TokenType.ID, "Expected loop variable").value
        self._consume(TokenType.ASSIGN, "Expected =")
        
        start = self.parse_expression(stop_tokens=[TokenType.RPAREN, TokenType.LPAREN])
        
        step = None
        if self._match(TokenType.LPAREN):
            step = self.parse_expression(stop_tokens=[TokenType.RPAREN])
            self._consume(TokenType.RPAREN, "Expected )")
        
        self._consume(TokenType.ASSIGN_INPUT, "Expected &=")
        end = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        
        return ForLoop(var_name, start, end, body, step)

    def parse_while(self) -> WhileLoop:
        # @loop(cond) **Loop** <for.f.whle>@also [ ... ]
        self._consume(TokenType.LOOP_CTRL, "Expected @loop")
        self._consume(TokenType.LPAREN, "Expected (")
        condition = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        
        self._consume(TokenType.LOOP, "Expected **Loop**")
        self._consume(TokenType.WHILE_ALSO, "Expected <for.f.whle>@also")
        
        self._consume(TokenType.LBRACKET, "Expected [")
        body = []
        while not self._check(TokenType.RBRACKET):
            body.append(self.parse_statement())
        self._consume(TokenType.RBRACKET, "Expected ]")
        
        return WhileLoop(condition, body)

    def parse_now(self) -> NowMutation:
        self._consume(TokenType.NOW, "Expected <now>")
        self._consume(TokenType.LPAREN, "Expected (")
        expr = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        self._consume(TokenType.GT, "Expected >")
        target = self._consume(TokenType.ID, "Expected target variable").value
        return NowMutation(expr, Identifier(target))

    def parse_expression(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        return self.parse_logical_or(stop_tokens)

    def parse_logical_or(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        expr = self.parse_logical_and(stop_tokens)
        while self._check_not_stop(TokenType.OR, stop_tokens) and self._match(TokenType.OR):
            op = TokenType.OR
            right = self.parse_logical_and(stop_tokens)
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_logical_and(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        expr = self.parse_comparison(stop_tokens)
        while self._check_not_stop(TokenType.AND, stop_tokens) and self._match(TokenType.AND):
            op = TokenType.AND
            right = self.parse_comparison(stop_tokens)
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_comparison(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        expr = self.parse_term(stop_tokens)
        while True:
            if self._check_any(TokenType.GT, TokenType.GE, TokenType.LE, TokenType.EQ, TokenType.NE):
                op = self._peek().type
                if stop_tokens and op in stop_tokens:
                    break
                self._advance()
                right = self.parse_term(stop_tokens)
                expr = BinaryOp(expr, op, right)
            elif self._check(TokenType.LANGLE) and self._peek(1).type != TokenType.DOLLAR:
                if stop_tokens and TokenType.LANGLE in stop_tokens:
                    break
                self._advance()
                op = TokenType.LANGLE
                right = self.parse_term(stop_tokens)
                expr = BinaryOp(expr, op, right)
            else:
                break
        return expr

    def parse_term(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        expr = self.parse_factor(stop_tokens)
        while self._check_not_stop(TokenType.PLUS, TokenType.MINUS, stop_tokens=stop_tokens) and self._match(TokenType.PLUS, TokenType.MINUS):
            op = self.tokens[self.pos-1].type
            right = self.parse_factor(stop_tokens)
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_factor(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        expr = self.parse_unary(stop_tokens)
        while self._check_not_stop(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT, stop_tokens=stop_tokens) and self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.tokens[self.pos-1].type
            right = self.parse_unary(stop_tokens)
            expr = BinaryOp(expr, op, right)
        return expr

    def parse_unary(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        if self._match(TokenType.MINUS):
            expr = self.parse_unary(stop_tokens)
            return UnaryOp(TokenType.MINUS, expr)
        if self._match(TokenType.TILDE):
            if self._check(TokenType.ID) and self._peek(1).type == TokenType.LPAREN:
                func_name = self._consume(TokenType.ID, "Expected function name").value
                self._consume(TokenType.LPAREN, "Expected (")
                args = self.parse_call_args()
                return Call(func_name, args)
            elif self._check(TokenType.DOLLAR):
                return self.parse_dollar_reference(stop_tokens)
            self._error("Expected function call after ~ sigil")
        return self.parse_primary(stop_tokens)

    def _check_not_stop(self, *types: TokenType, stop_tokens: Optional[List[TokenType]] = None) -> bool:
        if not self._check_any(*types):
            return False
        if stop_tokens and self._peek().type in stop_tokens:
            return False
        return True

    def _check_any(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                return True
        return False

    def parse_primary(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        expr = self._parse_base_primary(stop_tokens)
        
        # Handle suffixes: indexing <index> and method calls $instance~method()
        while True:
            next_token = self._peek()
            if next_token.type == TokenType.LANGLE and (stop_tokens is None or TokenType.LANGLE not in stop_tokens) and next_token.line == self.tokens[self.pos-1].line and next_token.column == self.tokens[self.pos-1].column + len(str(self.tokens[self.pos-1].value)):
                # target<index> with no space
                self._advance()
                indices = []
                while True:
                    # Index expressions should stop at > or another <
                    indices.append(self.parse_expression(stop_tokens=[TokenType.RANGLE, TokenType.LANGLE]))
                    if not self._match(TokenType.LANGLE):
                        break
                self._consume(TokenType.RANGLE, "Expected >")
                expr = Indexing(expr, indices)
            elif next_token.type == TokenType.LBRACE and (stop_tokens is None or TokenType.LBRACE not in stop_tokens) and next_token.line == self.tokens[self.pos-1].line and next_token.column == self.tokens[self.pos-1].column + len(str(self.tokens[self.pos-1].value)):
                # Dictionary key access: expr{key}
                self._advance()
                self._dict_literal_depth += 1
                try:
                    key = self.parse_expression(stop_tokens=[TokenType.RBRACE])
                finally:
                    self._dict_literal_depth -= 1
                self._consume(TokenType.RBRACE, "Expected }")
                if isinstance(expr, Literal) and self._dict_literal_depth == 0:
                    expr = DictLiteral({expr: key})
                else:
                    expr = Indexing(expr, [key])
            elif self._match(TokenType.DOLLAR):
                # $instance~method(args)
                method_name = self._consume(TokenType.ID, "Expected method name").value
                self._consume(TokenType.TILDE, "Expected ~")
                self._consume(TokenType.LPAREN, "Expected (")
                args = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self.parse_expression(stop_tokens=[TokenType.RPAREN]))
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected )")
                expr = Call(method_name, args, is_instance_method=True, instance=expr.name if isinstance(expr, Identifier) else None)
            elif self._match(TokenType.TILDE):
                # base~method(args) - instance method call after expression base
                if self._check(TokenType.ID) and self._peek(1).type == TokenType.LPAREN:
                    method_name = self._consume(TokenType.ID, "Expected method name").value
                    self._consume(TokenType.LPAREN, "Expected (")
                    args = []
                    if not self._check(TokenType.RPAREN):
                        while True:
                            args.append(self.parse_expression(stop_tokens=[TokenType.RPAREN]))
                            if not self._match(TokenType.COMMA):
                                break
                    self._consume(TokenType.RPAREN, "Expected )")
                    expr = Call(method_name, args, is_instance_method=True, instance=expr.name if isinstance(expr, Identifier) else None)
                else:
                    break
            elif next_token.type == TokenType.LPAREN and (stop_tokens is None or TokenType.LPAREN not in stop_tokens):
                self._advance()
                # Function call: expr(args)
                args = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self.parse_expression(stop_tokens=[TokenType.RPAREN, TokenType.COMMA]))
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected )")
                expr = Call(expr.name if isinstance(expr, Identifier) else str(expr), args)
            else:
                break
        return expr

    def _parse_base_primary(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        if self._match(TokenType.INT, TokenType.FREAL, TokenType.STRING, TokenType.BOOL):
            return Literal(self.tokens[self.pos-1].value)
        
        if self._match(TokenType.ID):
            return Identifier(self.tokens[self.pos-1].value)
        
        if self._check(TokenType.LANGLE):
            return self.parse_system_tag_or_index(stop_tokens)
        
        if self._check(TokenType.ENCODE):
            return self.parse_encode()
        
        if self._check(TokenType.LEN):
            return self.parse_len()
        
        if self._check(TokenType.DOLLAR):
            return self.parse_dollar_reference(stop_tokens)

        if self._check(TokenType.LBRACE):
            self._advance()
            if self._check(TokenType.COLON):
                self._advance()
                value = self.parse_expression(stop_tokens=[TokenType.RBRACE])
                self._consume(TokenType.RBRACE, "Expected }")
                return DictLiteral({Literal(""): value})
            key = self.parse_expression(stop_tokens=[TokenType.COLON, TokenType.RBRACE])
            if self._match(TokenType.COLON):
                mapping = {}
                mapping[key] = self.parse_expression(stop_tokens=[TokenType.RBRACE])
                while self._match(TokenType.COMMA):
                    k = self.parse_expression(stop_tokens=[TokenType.COLON, TokenType.RBRACE])
                    self._consume(TokenType.COLON, "Expected :")
                    v = self.parse_expression(stop_tokens=[TokenType.RBRACE])
                    mapping[k] = v
                self._consume(TokenType.RBRACE, "Expected }")
                return DictLiteral(mapping)
            self._consume(TokenType.RBRACE, "Expected }")
            return key

        if self._match(TokenType.LPAREN):
            elements = []
            if not self._check(TokenType.RPAREN):
                while True:
                    elements.append(self.parse_expression(stop_tokens=[TokenType.RPAREN]))
                    if not self._match(TokenType.COMMA):
                        break
            if len(elements) == 1 and self._check(TokenType.LBRACE):
                key = elements[0]
                self._advance()
                value = self.parse_expression(stop_tokens=[TokenType.RBRACE])
                self._consume(TokenType.RBRACE, "Expected }")
                self._consume(TokenType.RPAREN, "Expected )")
                return DictLiteral({key: value})
            self._consume(TokenType.RPAREN, "Expected )")
            if len(elements) == 1:
                if self._peek().type == TokenType.TILDE:
                    return TupleLiteral(elements)
                return elements[0]
            return TupleLiteral(elements)

        self._error(f"Expected expression, found {self._peek().type}")

    def parse_dollar_reference(self, stop_tokens=None) -> Expr:
        """Handle $ references in expression context like $random or $module(args)"""
        self._advance()  # consume $
        if self._check(TokenType.ID):
            name = self._consume(TokenType.ID, "Expected identifier after $").value
            if self._check(TokenType.LPAREN):
                # $module(args) - module function call
                self._advance()  # consume (
                args = self.parse_call_args()
                self._consume(TokenType.RPAREN, "Expected )")
                return Call(name, args)
            return Identifier(name)
        self._error("Expected identifier after $ in expression")
        return Identifier("")

    def parse_call_or_instantiation(self) -> Stmt:
        # ~tên_hàm(args) or ~TênClass~tên_instance or $instance*method(args)
        if self._match(TokenType.TILDE, TokenType.STAR):
            name = self._consume(TokenType.ID, "Expected name").value
            if self._match(TokenType.LPAREN):
                # Call
                args = self.parse_call_args()
                return Call(name, args)
            elif self._match(TokenType.TILDE, TokenType.STAR):
                # Instantiation
                instance_name = self._consume(TokenType.ID, "Expected instance name").value
                return VarDecl(name, None, instance_name, is_instantiation=True)
        elif self._match(TokenType.DOLLAR):
            # $instance*method
            instance = self._consume(TokenType.ID, "Expected instance").value
            self._match(TokenType.TILDE, TokenType.STAR) # Consume sigil
            method_name = self._consume(TokenType.ID, "Expected method name").value
            self._consume(TokenType.LPAREN, "Expected (")
            args = self.parse_call_args()
            self._consume(TokenType.RPAREN, "Expected )")
            return Call(method_name, args, is_instance_method=True, instance=instance)
        
        self._error("Invalid call or instantiation")

    def parse_call_args(self) -> List[Expr]:
        args = []
        if not self._check(TokenType.RPAREN):
            while True:
                args.append(self.parse_expression(stop_tokens=[TokenType.RPAREN, TokenType.COMMA]))
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RPAREN, "Expected )")
        return args

    def parse_memory(self) -> Stmt:
        self._consume(TokenType.MEMORY, "Expected <memory>")
        # Could be <memory>^h or <memory>dete(h)
        if self._match(TokenType.CARET):
            target = self._consume(TokenType.ID, "Expected identifier").value
            return Call("memory_addr", [Identifier(target)])
        elif self._match(TokenType.ID):
            func = self.tokens[self.pos-1].value
            if func == "dete":
                self._consume(TokenType.LPAREN, "Expected (")
                target = self._consume(TokenType.ID, "Expected identifier").value
                self._consume(TokenType.RPAREN, "Expected )")
                return Call("memory_free", [Identifier(target)], target=target)
        
        self._error("Invalid memory operation")

    def parse_print(self) -> Stmt:
        is_printf = self._peek().type == TokenType.PRINTF
        self._advance() # Consume <print> or <printf>
        
        if not is_printf:
            self._consume(TokenType.ID, "Expected type (string)")
            
        self._consume(TokenType.CARET, "Expected ^")
        self._consume(TokenType.LPAREN, "Expected (")
        
        if is_printf:
            parts = []
            exprs = []
            current_text = ""
            while not self._check(TokenType.RPAREN):
                token = self._advance()
                if token.type == TokenType.LBRACE:
                    parts.append(Literal(current_text))
                    current_text = ""
                    expr = self.parse_expression(stop_tokens=[TokenType.RBRACE])
                    self._consume(TokenType.RBRACE, "Expected }")
                    exprs.append(expr)
                elif token.type == TokenType.STRING:
                    current_text += token.value
                elif token.type == TokenType.RPAREN:
                    break
                else:
                    self._error(f"Unexpected token '{token.type}' in printf format string. String literals must be enclosed in quotes, and escape sequences like /n must be inside quotes")
            
            if current_text:
                parts.append(Literal(current_text))
            
            self._consume(TokenType.RPAREN, "Expected )")
            return Call("printf", [Literal(parts)] + exprs)
        else:
            expr = self.parse_expression(stop_tokens=[TokenType.RPAREN])
            trailing_str = None
            if self._check(TokenType.STRING):
                trailing_str = self._advance().value
            self._consume(TokenType.RPAREN, "Expected )")
            if trailing_str is not None:
                return Call("print", [expr, Literal(trailing_str)])
            return Call("print", [expr])

    def parse_input(self) -> Stmt:
        self._consume(TokenType.INPUT, "Expected <input>")
        self._consume(TokenType.LPAREN, "Expected (")
        prompt = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        
        if self._match(TokenType.ASSIGN_INPUT):
            # <input>(...)&=string("")~name
            # or <input>(...)&=type~name
            # or <input>(...)&=name
            if self._check(TokenType.ID) and self._peek(1).type == TokenType.LPAREN:
                # New var decl with initializer: type(val)~name
                decl = self.parse_var_decl()
                return Assignment(Identifier(decl.name), Call("input", [prompt]), type_name=decl.type_name)
            elif self._check(TokenType.ID) and self._peek(1).type == TokenType.TILDE:
                # New var decl without initializer: type~name
                type_name = self._consume(TokenType.ID, "Expected type name").value
                self._consume(TokenType.TILDE, "Expected ~")
                name = self._consume(TokenType.ID, "Expected variable name").value
                return Assignment(Identifier(name), Call("input", [prompt]), type_name=type_name)
            else:
                target = self._consume(TokenType.ID, "Expected target variable").value
                return Assignment(Identifier(target), Call("input", [prompt]))

        if isinstance(prompt, Identifier):
            return Assignment(prompt, Call("input", [prompt]))

        return Call("input", [prompt])

    def parse_return(self) -> Stmt:
        self._consume(TokenType.RETURN, "Expected <return>")
        self._consume(TokenType.LPAREN, "Expected (")
        expr = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        return Call("return", [expr])

    def parse_system_tag_or_index(self, stop_tokens: Optional[List[TokenType]] = None) -> Expr:
        # We know next is LANGLE
        self._advance()
        if self._match(TokenType.DOLLAR):
            # <$random>(...) or <$web>domain(...)
            module_name = self._consume(TokenType.ID, "Expected module name").value
            self._consume(TokenType.RANGLE, "Expected >")
            
            func_name = None
            if self._check(TokenType.ID):
                func_name = self._advance().value
            
            self._match(TokenType.CARET) # Consume ^ if present
            
            args = []
            if self._match(TokenType.LPAREN):
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self.parse_expression(stop_tokens=[TokenType.RPAREN, TokenType.COMMA]))
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected )")
            
            full_name = f"{module_name}.{func_name}" if func_name else module_name
            target = None
            if self._check(TokenType.ID) and self._peek().value.startswith("@"):
                target = self._advance().value[1:]
            
            return Call(full_name, args, target=target)
        
        self._error("Unexpected '<' in expression (expected module call <$module>)")



class KoInterpreter:
    def __init__(self, program: Program):
        self.program = program
        self.scopes = [{}]
        self.functions = {}
        self.classes = {}
        self._recursion_depth = 0
        self._loop_iterations = 0
        self._loop_optimization_reports = []

    def push_scope(self):
        self.scopes.append({})
    
    def pop_scope(self):
        self.scopes.pop()
    
    def get_var(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise NameError(f"Name '{name}' is not defined")
    
    def set_var(self, name, value):
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = value
                return
        self.scopes[-1][name] = value

    def run(self):
        for decl in self.program.decls:
            if isinstance(decl, FuncDecl):
                self.functions[decl.name] = decl
            elif isinstance(decl, ClassDecl):
                self.visit(decl)
        
        for imp in self.program.imports:
            self.visit(imp)
        
        if self.program.main:
            self.visit(self.program.main)
    
    def visit(self, node: Node):
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
        
    def generic_visit(self, node: Node):
        raise NotImplementedError(f"No visit_{node.__class__.__name__} method")

    def visit_MainBlock(self, node: MainBlock):
        self.push_scope()
        catch_blocks = self._collect_catch_blocks(node.body)
        global_catch_blocks = self.program.catch_blocks
        all_catch_blocks = catch_blocks + global_catch_blocks
        for stmt in node.body:
            try:
                self.visit(stmt)
            except ReturnException as e:
                self.pop_scope()
                return e.value
            except KeyNotFoundError as exc:
                self._handle_catch_in_scope("KeyNotFoundError", exc, all_catch_blocks)
            except Exception as exc:
                error_type = type(exc).__name__
                mapped = self._map_python_error(error_type)
                self._handle_catch_in_scope(mapped, exc, all_catch_blocks)
        self.pop_scope()

    def _map_python_error(self, error_type: str) -> str:
        mapping = {
            "ZeroDivisionError": "DivideByZeroError",
            "KeyError": "KeyNotFoundError",
            "TypeError": "TypeError",
            "ValueError": "ValueError",
            "IndexError": "IndexError",
            "AttributeError": "AttributeError",
            "NameError": "NameError",
        }
        return mapping.get(error_type, error_type)

    def _collect_catch_blocks(self, stmts):
        catch_blocks = []
        for stmt in stmts:
            if isinstance(stmt, CatchStmt):
                catch_blocks.append(stmt)
        return catch_blocks

    def _handle_catch_in_scope(self, error_type, exc, catch_blocks):
        # Combine statically collected catch blocks with dynamically registered ones
        all_catch_blocks = list(catch_blocks)
        scope = self.scopes[-1]
        dynamic_catch_blocks = scope.get("_catch_blocks", [])
        all_catch_blocks.extend(dynamic_catch_blocks)
        
        for catch in all_catch_blocks:
            if isinstance(catch.error_condition, str):
                error_code = catch.error_condition.strip("`")
                if error_code == error_type:
                    self.scopes[-1]["error"] = {
                        "line": 0,
                        "code": error_code,
                        "type": error_type,
                    }
                    for stmt in catch.body:
                        self.visit(stmt)
                    return
            elif isinstance(catch.error_condition, Expr):
                cond = self.visit(catch.error_condition)
                if cond:
                    self.scopes[-1]["error"] = {
                        "line": 0,
                        "code": str(exc),
                        "type": error_type,
                    }
                    for stmt in catch.body:
                        self.visit(stmt)
                    return
        raise KoCompileError(f"{error_type}: {exc}")

    def visit_ClassDecl(self, node: ClassDecl):
        class_name = node.name
        methods = {}
        attrs = {}
        
        for stmt in node.body + node.private_body:
            if isinstance(stmt, FuncDecl):
                methods[stmt.name] = stmt
            elif isinstance(stmt, VarDecl):
                attrs[stmt.name] = self.visit(stmt.initializer) if stmt.initializer else None
        
        def constructor(cls, **kwargs):
            instance = {"__class__": class_name}
            for name, value in attrs.items():
                instance[name] = value
            for name, value in kwargs.items():
                instance[name] = value
            return instance
        
        def make_method(method_decl):
            def method_func(instance, *args):
                self._recursion_depth += 1
                if self._recursion_depth > MAX_RECURSION_DEPTH:
                    raise KoCompileError(f"Maximum recursion depth exceeded")
                old_scopes = self.scopes
                self.scopes = [dict(instance)]
                for i, param in enumerate(method_decl.params):
                    self.scopes[-1][param.name] = args[i] if i < len(args) else None
                try:
                    for stmt in method_decl.body:
                        self.visit(stmt)
                except ReturnException as e:
                    self.scopes = old_scopes
                    self._recursion_depth -= 1
                    return e.value
                self.scopes = old_scopes
                self._recursion_depth -= 1
                return None
            return method_func
        
        bound_methods = {}
        for name, method in methods.items():
            bound_methods[name] = make_method(method)
        
        new_class = type(class_name, (object,), {**bound_methods, '__init__': constructor})
        self.classes[class_name] = new_class

    def visit_FuncDecl(self, node: FuncDecl) -> None:
        # Register function for global lookup and local access
        self.functions[node.name] = node
        # Also store in current scope to support nested/local function declarations
        self.set_var(node.name, node)

    def visit_CatchStmt(self, node: CatchStmt):
        # Register catch block with current scope for dynamic exception handling
        # This allows catch blocks inside control flow (if/for/while) to be active
        scope = self.scopes[-1]
        if "_catch_blocks" not in scope:
            scope["_catch_blocks"] = []
        scope["_catch_blocks"].append(node)

    def visit_ImportStmt(self, node: ImportStmt) -> None:
        import json
        import subprocess
        compiler_dir = os.path.dirname(os.path.abspath(__file__))
        import_java = os.path.join(compiler_dir, "Import.java")
        import_class = os.path.join(compiler_dir, "Import.class")
        if not os.path.exists(import_class):
            result = subprocess.run(
                ["javac", import_java],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                raise KoCompileError(f"javac failed: {result.stderr.strip()}")
        result = subprocess.run(
            ["java", "-cp", compiler_dir, "Import",
             node.module_name, node.alias, node.scope_tag],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            raise KoCompileError(f"Import.java failed: {result.stderr.strip()}")
        try:
            module_info = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            raise KoCompileError(f"Import.java returned invalid JSON: {result.stdout.strip()}")
        self.set_var(node.alias, module_info)

    def visit_WhileLoop(self, node: WhileLoop):
        for _ in range(MAX_LOOP_ITERATIONS):
            if not self.visit(node.condition):
                break
            self._loop_iterations += 1
            if self._loop_iterations > MAX_LOOP_ITERATIONS:
                raise KoCompileError(f"Maximum loop iterations ({MAX_LOOP_ITERATIONS}) exceeded")
            for stmt in node.body:
                self.visit(stmt)

    def visit_IfStmt(self, node: IfStmt):
        if self.visit(node.condition):
            for stmt in node.body:
                self.visit(stmt)
        elif node.else_body:
            if isinstance(node.else_body, IfStmt):
                self.visit(node.else_body)
            else:
                for stmt in node.else_body:
                    self.visit(stmt)

    def _try_loop_engine(self, var_name, start, end, step, body):
        import subprocess
        import tempfile
        compiler_dir = os.path.dirname(os.path.abspath(__file__))
        loop_engine = os.path.join(compiler_dir, "LoopEngine")
        if not os.path.exists(loop_engine):
            loop_cpp = os.path.join(compiler_dir, "Loop.cpp")
            if not os.path.exists(loop_cpp):
                raise KoCompileError(f"LoopEngine binary not found and Loop.cpp source not available at {loop_cpp}")
            result = subprocess.run(
                ["g++", "-std=c++11", "-O2", loop_cpp, "-o", loop_engine],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                raise KoCompileError(f"g++ failed to compile Loop.cpp: {result.stderr.strip()}")
        body_file = None
        try:
            body_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            for stmt in body:
                body_file.write(f"visit({stmt.__class__.__name__})\n")
            body_file.close()
            result = subprocess.run(
                [loop_engine, var_name, str(start), str(end), str(step), body_file.name, "1"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise KoCompileError(f"LoopEngine failed: {result.stderr.strip()}")
            return result.stdout.strip()
        finally:
            if body_file and os.path.exists(body_file.name):
                os.unlink(body_file.name)

    def visit_ForLoop(self, node: ForLoop):
        start = self.visit(node.start)
        end = self.visit(node.end)
        step = self.visit(node.step) if node.step else 1

        if step == 0:
            raise KoCompileError("Loop step cannot be zero")

        total_iterations = max(0, (end - start) // step + 1) if (step > 0 and start <= end) or (step < 0 and start >= end) else 0
        if total_iterations > MAX_LOOP_ITERATIONS:
            raise KoCompileError(f"Loop iteration count ({total_iterations}) exceeds maximum ({MAX_LOOP_ITERATIONS})")

        loop_report = self._try_loop_engine(node.var_name, start, end, step, node.body)
        if loop_report:
            self._loop_optimization_reports.append(loop_report)

        for i in range(start, end + 1, step):
            self._loop_iterations += 1
            if self._loop_iterations > MAX_LOOP_ITERATIONS:
                raise KoCompileError(f"Maximum loop iterations ({MAX_LOOP_ITERATIONS}) exceeded")
            self.set_var(node.var_name, i)
            for stmt in node.body:
                self.visit(stmt)

    def visit_Call(self, node: Call):
        args = [self.visit(arg) for arg in node.args]
        handler = self._call_handlers.get(node.name)
        if handler is not None:
            return handler(self, args, node)
        module_info = None
        if isinstance(node.name, str):
            try:
                module_info = self.get_var(node.name)
            except NameError:
                pass
        if isinstance(module_info, dict) and "module" in module_info:
            module_name = module_info["module"]
            handler = self._call_handlers.get(module_name)
            if handler is None:
                handler = self._call_handlers.get(module_name.lower())
            if handler is not None:
                return handler(self, args, node)
        self._recursion_depth += 1
        if self._recursion_depth > MAX_RECURSION_DEPTH:
            self._recursion_depth -= 1
            raise KoCompileError(f"Maximum recursion depth ({MAX_RECURSION_DEPTH}) exceeded")
        try:
            if node.name in self.functions:
                func = self.functions[node.name]
                self.push_scope()
                for i, param in enumerate(func.params):
                    self.set_var(param.name, args[i])
                func_catch_blocks = self._collect_catch_blocks(func.body)
                try:
                    for stmt in func.body:
                        try:
                            self.visit(stmt)
                        except ReturnException as e:
                            self.pop_scope()
                            self._recursion_depth -= 1
                            return e.value
                        except KeyNotFoundError as exc:
                            self._handle_catch_in_scope("KeyNotFoundError", exc, func_catch_blocks)
                        except Exception as exc:
                            error_type = type(exc).__name__
                            mapped = self._map_python_error(error_type)
                            self._handle_catch_in_scope(mapped, exc, func_catch_blocks)
                except ReturnException as e:
                    self.pop_scope()
                    self._recursion_depth -= 1
                    return e.value
                self.pop_scope()
                self._recursion_depth -= 1
                return None
            elif node.is_instance_method and node.instance:
                try:
                    obj = self.get_var(node.instance)
                except NameError:
                    return None
                if isinstance(obj, dict) and "__class__" in obj:
                    class_name = obj["__class__"]
                    if class_name in self.classes:
                        cls = self.classes[class_name]
                        if hasattr(cls, node.name):
                            return getattr(cls, node.name)(obj, *args)
                elif hasattr(obj, node.name):
                    return getattr(obj, node.name)(obj, *args)
                return None
            else:
                self._recursion_depth -= 1
                raise NameError(f"Function {node.name} not defined")
        except KoCompileError:
            self._recursion_depth -= 1
            raise

    @staticmethod
    def _handle_print(ko_self, args, node):
        if len(args) == 2 and isinstance(node.args[1], Literal) and isinstance(node.args[1].value, str):
            print(str(args[0]) + args[1])
        else:
            print(*args)

    @staticmethod
    def _handle_memory_addr(ko_self, args, node):
        return id(args[0]) if args else None

    @staticmethod
    def _handle_memory_free(ko_self, args, node):
        var_name = node.target if node.target else None
        if var_name:
            try:
                ko_self.set_var(var_name, None)
            except NameError:
                pass
        return None

    @staticmethod
    def _handle_printf(ko_self, args, node):
        parts = args[0] if args else []
        exprs = args[1:]
        if isinstance(parts, list):
            format_parts = []
            for i, part in enumerate(parts):
                if isinstance(part, Literal):
                    if isinstance(part.value, str):
                        format_parts.append(part.value)
                    else:
                        format_parts.append(str(part.value))
                elif isinstance(part, str):
                    format_parts.append(part)
                else:
                    format_parts.append(str(part))
                if i < len(exprs):
                    format_parts.append(str(exprs[i]))
            fmt_str = "".join(format_parts)
        else:
            fmt_str = str(parts)
        print(fmt_str, end='')

    @staticmethod
    def _handle_input(ko_self, args, node):
        return input(args[0] if args else "")

    @staticmethod
    def _handle_return(ko_self, args, node):
        raise ReturnException(args[0] if args else None)

    @staticmethod
    def _handle_random(ko_self, args, node):
        import random as _random
        return _random.randint(args[0], args[1])

    @staticmethod
    def _handle_os(ko_self, args, node):
        import os as _os
        if len(args) == 1:
            path = args[0]
            if not _is_safe_os_path(path):
                raise KoCompileError(f"Security violation: path '{path}' is not in allowed paths")
            try:
                f = open(path, "r")
                content = f.read()
                f.close()
                return content
            except FileNotFoundError:
                return ""
        return ""

    @staticmethod
    def _handle_web(ko_self, args, node):
        return ""

    @staticmethod
    def _handle_domain(ko_self, args, node):
        return args[0] if args else ""

    @staticmethod
    def _handle_web_domain(ko_self, args, node):
        return args[0] if args else ""

    @staticmethod
    def _handle_web_fetch(ko_self, args, node):
        import urllib.request
        from urllib.parse import urlparse
        if args:
            url = args[0]
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise KoCompileError(f"Security violation: URL scheme '{parsed.scheme}' is not allowed for web.fetch")
            try:
                response = urllib.request.urlopen(url)
                return response.read().decode('utf-8')
            except Exception:
                return ""
        return ""

    @staticmethod
    def _handle_web_status(ko_self, args, node):
        import urllib.request
        from urllib.parse import urlparse
        if args:
            url = args[0]
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise KoCompileError(f"Security violation: URL scheme '{parsed.scheme}' is not allowed for web.status")
            try:
                response = urllib.request.urlopen(url)
                return response.read().decode('utf-8')
            except Exception:
                return ""
        return ""

    @staticmethod
    def _handle_os_read_file(ko_self, args, node):
        if args:
            path = args[0]
            if not _is_safe_os_path(path):
                raise KoCompileError(f"Security violation: path '{path}' is not in allowed paths")
            try:
                with open(path, 'r') as f:
                    return f.read()
            except FileNotFoundError:
                return ""
        return ""

    @staticmethod
    def _handle_os_write_file(ko_self, args, node):
        if len(args) >= 2:
            path = args[0]
            if not _is_safe_os_path(path):
                raise KoCompileError(f"Security violation: path '{path}' is not in allowed paths")
            try:
                with open(path, 'w') as f:
                    f.write(args[1])
                return True
            except Exception:
                return False
        return False

    @staticmethod
    def _handle_os_list_dir(ko_self, args, node):
        import os
        if args:
            try:
                return os.listdir(args[0])
            except Exception:
                return []
        return []

    @staticmethod
    def _handle_random_random_int(ko_self, args, node):
        import random
        if len(args) >= 2:
            return random.randint(args[0], args[1])
        return 0

    @staticmethod
    def _handle_byte(ko_self, args, node):
        return to_byte(args[0]) if args else None

    @staticmethod
    def _handle_bytes(ko_self, args, node):
        if len(args) == 1:
            val = args[0]
            if isinstance(val, str):
                try:
                    int(val, 16)
                    return bytes.fromhex(val)
                except ValueError:
                    return int(val) * b'\x00'
            return b'\x00' * int(val)
        return bytes(args[0])

    @staticmethod
    def _handle_encode(ko_self, args, node):
        if len(args) >= 2:
            encoding_map = {"ASCII": "ascii", "UTF-8": "utf-8", "UTF-16": "utf-16"}
            encoding = encoding_map.get(str(args[1]).strip("'\""), "utf-8")
            return str(args[0]).encode(encoding)
        return str(args[0]).encode('utf-8')

    @staticmethod
    def _handle_len(ko_self, args, node):
        if not args:
            return 0
        val = args[0]
        if val is None:
            return 0
        if isinstance(val, (str, bytes, list, tuple, dict)):
            try:
                return min(len(val), 1073741824)
            except Exception:
                return 0
        return 0

    _call_handlers = {
        "print": _handle_print,
        "memory_addr": _handle_memory_addr,
        "memory_free": _handle_memory_free,
        "printf": _handle_printf,
        "input": _handle_input,
        "return": _handle_return,
        "random": _handle_random,
        "os": _handle_os,
        "web": _handle_web,
        "domain": _handle_domain,
        "web.domain": _handle_web_domain,
        "web.fetch": _handle_web_fetch,
        "web.status": _handle_web_status,
        "os.read_file": _handle_os_read_file,
        "os.write_file": _handle_os_write_file,
        "os.list_dir": _handle_os_list_dir,
        "random.random_int": _handle_random_random_int,
        "byte": _handle_byte,
        "bytes": _handle_bytes,
        "encode": _handle_encode,
        "len": _handle_len,
    }

    def visit_VarDecl(self, node: VarDecl):
        if node.is_instantiation:
            class_name = node.initializer or node.type_name
            if class_name in self.classes:
                cls = self.classes[class_name]
                instance = cls.__init__(cls)
                self.set_var(node.name, instance)
            else:
                self.set_var(node.name, None)
        else:
            val = self.visit(node.initializer) if node.initializer else None
            if node.type_name:
                val = self._convert_value(val, node.type_name)
            self.set_var(node.name, val)

    def visit_Assignment(self, node: Assignment):
        val = self.visit(node.value)
        if node.type_name:
            val = self._convert_value(val, node.type_name)
        self.set_var(node.target.name, val)

    def _convert_value(self, value, type_name: str):
        if type_name == "int":
            try:
                return int(value)
            except (ValueError, TypeError):
                raise KoCompileError(f"TypeError: cannot convert '{value}' ('{type(value).__name__}') to int")
        elif type_name == "freal":
            try:
                return float(value)
            except (ValueError, TypeError):
                raise KoCompileError(f"TypeError: cannot convert '{value}' ('{type(value).__name__}') to freal")
        elif type_name == "booling":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                low = value.strip().lower()
                if low in ("true", "1", "yes"):
                    return True
                elif low in ("false", "0", "no", ""):
                    return False
                raise KoCompileError(f"TypeError: cannot convert '{value}' to booling")
            return bool(value)
        elif type_name == "string":
            return str(value)
        elif type_name == "byte":
            return to_byte(value)
        elif type_name == "bytes":
            if isinstance(value, bytes):
                return value
            if isinstance(value, str):
                try:
                    return bytes.fromhex(value)
                except ValueError:
                    return value.encode("utf-8")
            if isinstance(value, int):
                return b"\x00" * value
            raise KoCompileError(f"TypeError: cannot convert '{value}' to bytes")
        return value

    def visit_NowMutation(self, node: NowMutation):
        val = self.visit(node.expr)
        self.set_var(node.target.name, val)

    def visit_Identifier(self, node: Identifier):
        return self.get_var(node.name)

    def visit_Indexing(self, node: Indexing):
        target = self.visit(node.target)
        for idx in node.index:
            index_val = self.visit(idx)
            try:
                target = target[index_val]
            except KeyError:
                target_name = ""
                if isinstance(node.target, Identifier):
                    target_name = node.target.name
                raise KeyNotFoundError(index_val, target_name)
        return target

    def visit_Literal(self, node: Literal):
        return node.value

    def visit_TupleLiteral(self, node: TupleLiteral):
        return tuple(self.visit(e) for e in node.elements)

    def visit_DictLiteral(self, node: DictLiteral):
        return {self.visit(k): self.visit(v) for k, v in node.mapping.items()}

    def visit_BinaryOp(self, node: BinaryOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.op == TokenType.PLUS: return left + right
        if node.op == TokenType.MINUS: return left - right
        if node.op == TokenType.STAR: return left * right
        if node.op == TokenType.TILDE: return left * right
        if node.op == TokenType.SLASH: return left / right
        if node.op == TokenType.PERCENT: return left % right
        if node.op == TokenType.AND: return left and right
        if node.op == TokenType.OR: return left or right
        if node.op == TokenType.EQ: return left == right
        if node.op == TokenType.NE: return left != right
        if node.op == TokenType.GT: return left > right
        if node.op == TokenType.GE: return left >= right
        if node.op == TokenType.LE: return left <= right
        if node.op == TokenType.LANGLE: return left < right
        raise NotImplementedError(f"Op {node.op} not implemented")

    def visit_UnaryOp(self, node: UnaryOp):
        expr = self.visit(node.expr)
        if node.op == TokenType.MINUS:
            return -expr
        return not expr

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value


class KeyNotFoundError(Exception):
    def __init__(self, key, target_name=""):
        self.key = key
        self.target_name = target_name
        super().__init__(f"KeyNotFoundError: key '{key}' not found in '{target_name}'")


def to_byte(value):
    if isinstance(value, bytes):
        return format(int.from_bytes(value, 'big'), '08b')
    if isinstance(value, str):
        if len(value) == 1:
            return format(ord(value), '08b')
        return format(int(value), '08b')
    if isinstance(value, int):
        return format(value, '08b')
    raise TypeError(f"Cannot convert '{value}' to byte")


ALLOWED_MODULES = {"Random", "Os", "Website"}
ALLOWED_URL_SCHEMES = {"http", "https"}
BANNED_URL_SCHEMES = {"file"}
SAFE_OS_PATHS = {"/tmp", "/home", "/workspace", "/workspaces"}
MAX_RECURSION_DEPTH = 100
MAX_LOOP_ITERATIONS = 1000000
MAX_STRING_LENGTH = 100000
MAX_SOURCE_SIZE = 10 * 1024 * 1024


class IRBuilder:
    def __init__(self):
        self.module = None
        self.current_function = None
        self.current_function_ir = None
        self.current_class = None
        self.basic_blocks = []
        self.current_block = None
        self.temp_counter = 0
        self.scope_stack = ["global"]

    def new_temp(self) -> str:
        self.temp_counter += 1
        return f"_t{self.temp_counter}"

    def new_label(self, prefix: str = "L") -> str:
        return f"{prefix}_{self.temp_counter}"

    def _qualified_name(self, name: str) -> str:
        parts = []
        if self.current_class:
            parts.append(self.current_class)
        if self.current_function:
            parts.append(self.current_function)
        parts.append(name)
        return ".".join(parts)

    def emit(self, opcode, arg=None, arg2=None, result=None, ir_type=None, line=0, op=None):
        from ir import IRInstruction, IROpcode, IRType
        if ir_type is None:
            ir_type = IRType.UNKNOWN
        instr = IRInstruction(
            opcode=opcode, arg=arg, arg2=arg2,
            result=result, type=ir_type, line=line, op=op
        )
        if self.current_block is not None:
            self.current_block.instructions.append(instr)
        return instr

    def emit_constant(self, value, ir_type=None, line=0):
        from ir import IRType, IROpcode
        if ir_type is None:
            ir_type = IRType.UNKNOWN
        result = self.new_temp()
        self.emit(IROpcode.LOAD_CONST, value, None, result, ir_type, line)
        return result

    def emit_load(self, name, ir_type=None, line=0):
        from ir import IRType, IROpcode
        if ir_type is None:
            ir_type = IRType.UNKNOWN
        result = self.new_temp()
        self.emit(IROpcode.LOAD_NAME, name, None, result, ir_type, line)
        return result

    def emit_store(self, name, value, ir_type=None, line=0):
        from ir import IROpcode
        self.emit(IROpcode.STORE_NAME, name, value, None, ir_type, line)

    def emit_binary_op(self, op, left, right, result, ir_type=None, line=0):
        from ir import IRType, IROpcode
        if ir_type is None:
            ir_type = IRType.UNKNOWN
        self.emit(IROpcode.BINARY_OP, left, right, result, ir_type, line, op=op)

    def emit_call(self, func_name, args, result, ir_type=None, line=0):
        from ir import IRType, IROpcode
        if ir_type is None:
            ir_type = IRType.UNKNOWN
        self.emit(IROpcode.CALL_FUNCTION, func_name, args, result, ir_type, line)

    def emit_return(self, value=None, line=0):
        from ir import IRType, IROpcode
        self.emit(IROpcode.RETURN_VALUE, value, None, None, IRType.NONE, line)

    def emit_print(self, value, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.PRINT_EXPR, value, None, None, IRType.NONE, line)

    def emit_printf(self, format_parts, args, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.PRINT_FORMAT, format_parts, args, None, IRType.NONE, line)

    def emit_input(self, prompt, result, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.INPUT_CALL, prompt, None, result, IRType.STRING, line)

    def emit_jump_if_false(self, condition, target, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.POP_JUMP_IF_FALSE, condition, target, None, IRType.NONE, line)

    def emit_jump(self, target, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.JUMP_FORWARD, target, None, None, IRType.NONE, line)

    def emit_pop(self, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.POP_TOP, None, None, None, IRType.NONE, line)

    def emit_nop(self, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.NOP, None, None, None, IRType.NONE, line)

    def emit_binary_subscr(self, target, index, result, ir_type=None, line=0):
        from ir import IRType, IROpcode
        if ir_type is None:
            ir_type = IRType.UNKNOWN
        self.emit(IROpcode.BINARY_SUBSCR, target, index, result, ir_type, line)

    def emit_store_subscr(self, target, index, value, line=0):
        from ir import IROpcode, IRType
        self.emit(IROpcode.STORE_SUBSCR, target, index, value, IRType.NONE, line)

    def start_block(self, name):
        from ir import IRBasicBlock
        block = IRBasicBlock(name)
        self.basic_blocks.append(block)
        self.current_block = block
        return block

    def end_block(self):
        self.current_block = None

    def build(self, program):
        from ir import IRModule, IRImport, IRFunction, IRClass, IRVariable, IRType, IRBasicBlock

        self.module = IRModule()

        for imp in program.imports:
            self.module.imports.append(IRImport(imp.module_name, imp.alias, imp.scope_tag))

        for decl in program.decls:
            if isinstance(decl, FuncDecl):
                self._build_function(decl)
            elif isinstance(decl, ClassDecl):
                self._build_class(decl)

        if program.main is not None:
            self._build_main(program.main)

        for catch in program.catch_blocks:
            self._build_catch(catch)

        return self.module

    def _build_function(self, func):
        from ir import IRFunction, IRVariable, IRType

        params = [IRVariable(p.name, self._type_name_to_ir_type(p.type_name), defined=True) for p in func.params]

        old_function = self.current_function
        old_basic_blocks = self.basic_blocks
        old_current_block = self.current_block
        self.current_function = func.name
        self.basic_blocks = []

        self.start_block(f"{func.name}_entry")
        for stmt in func.body:
            self._build_statement(stmt)
        self.end_block()

        func_ir = IRFunction(
            name=func.name,
            params=params,
            body=self.basic_blocks,
            return_type=IRType.UNKNOWN,
            local_vars={}
        )
        self.module.functions[func.name] = func_ir
        self.current_function = old_function
        self.basic_blocks = old_basic_blocks
        self.current_block = old_current_block

    def _build_class(self, cls):
        from ir import IRClass, IRVariable, IRType, IRFunction

        fields = {}
        methods = {}
        private_fields = {}
        private_methods = {}

        old_class = self.current_class
        qualified_name = self._qualified_name(cls.name)
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

        class_ir = IRClass(
            name=cls.name,
            fields=fields,
            methods=methods,
            private_fields=private_fields,
            private_methods=private_methods
        )
        self.module.classes[qualified_name] = class_ir
        self.current_class = old_class

    def _build_method_ir(self, func):
        from ir import IRFunction, IRVariable, IRType
        old_basic_blocks = self.basic_blocks
        old_current_block = self.current_block
        old_function = self.current_function
        old_function_ir = self.current_function_ir
        self.basic_blocks = []

        self.current_function = func.name
        self.current_function_ir = IRFunction(
            name=func.name,
            params=[IRVariable(p.name, self._type_name_to_ir_type(p.type_name), defined=True) for p in func.params],
            body=[],
            return_type=IRType.UNKNOWN,
            is_method=True,
            is_private=False
        )

        self.start_block(f"{func.name}_entry")
        for stmt in func.body:
            self._build_statement(stmt)
        self.end_block()

        self.current_function_ir.body = self.basic_blocks
        result = self.current_function_ir
        self.basic_blocks = old_basic_blocks
        self.current_block = old_current_block
        self.current_function = old_function
        self.current_function_ir = old_function_ir
        return result

    def _build_main(self, main):
        old_basic_blocks = self.basic_blocks
        old_current_block = self.current_block
        old_function = self.current_function
        old_function_ir = self.current_function_ir
        self.basic_blocks = []

        self.current_function = "__main__"
        self.current_function_ir = None

        self.start_block("main_entry")
        for stmt in main.body:
            self._build_statement(stmt)
        self.end_block()

        self.module.main = self.basic_blocks
        self.basic_blocks = old_basic_blocks
        self.current_block = old_current_block
        self.current_function = old_function
        self.current_function_ir = old_function_ir

    def _build_catch(self, catch):
        from ir import IRCatchBlock

        old_basic_blocks = self.basic_blocks
        self.basic_blocks = []

        self.start_block("catch_entry")
        for stmt in catch.body:
            self._build_statement(stmt)
        self.end_block()

        self.module.catch_blocks.append(IRCatchBlock(
            error_code=catch.error_condition if isinstance(catch.error_condition, str) else None,
            condition=str(catch.error_condition) if not isinstance(catch.error_condition, str) else None,
            body=self.basic_blocks
        ))
        self.basic_blocks = old_basic_blocks

    def _build_statement(self, stmt):
        if isinstance(stmt, VarDecl):
            self._build_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            self._build_assignment(stmt)
        elif isinstance(stmt, NowMutation):
            self._build_now_mutation(stmt)
        elif isinstance(stmt, IfStmt):
            self._build_if(stmt)
        elif isinstance(stmt, ForLoop):
            self._build_for_loop(stmt)
        elif isinstance(stmt, WhileLoop):
            self._build_while_loop(stmt)
        elif isinstance(stmt, FuncDecl):
            self._build_function(stmt)
        elif isinstance(stmt, ClassDecl):
            self._build_class(stmt)
        elif isinstance(stmt, Call):
            self._build_call(stmt)
        elif isinstance(stmt, ImportStmt):
            pass
        elif isinstance(stmt, CatchStmt):
            pass

    def _build_var_decl(self, stmt):
        from ir import IRVariable, IRType
        value_temp = None
        if stmt.initializer is not None:
            value_temp = self._build_expression(stmt.initializer)
        var_type = stmt.type_name or "unknown"
        ir_var = IRVariable(stmt.name, self._type_name_to_ir_type(var_type), defined=True)
        if self.current_function_ir is not None:
            self.current_function_ir.local_vars[stmt.name] = ir_var
        else:
            self.module.global_vars[stmt.name] = ir_var
        if value_temp is not None:
            self.emit_store(stmt.name, value_temp)

    def _build_assignment(self, stmt):
        value_temp = self._build_expression(stmt.value)
        self.emit_store(stmt.target.name, value_temp)

    def _build_now_mutation(self, stmt):
        self._build_expression(stmt.expr)

    def _build_if(self, stmt):
        self._build_expression(stmt.condition)
        for s in stmt.body:
            self._build_statement(s)
        if stmt.else_body:
            if isinstance(stmt.else_body, IfStmt):
                self._build_if(stmt.else_body)
            else:
                for s in stmt.else_body:
                    self._build_statement(s)

    def _build_for_loop(self, stmt):
        self._build_expression(stmt.start)
        self._build_expression(stmt.end)
        if stmt.step:
            self._build_expression(stmt.step)
        for s in stmt.body:
            self._build_statement(s)

    def _build_while_loop(self, stmt):
        self._build_expression(stmt.condition)
        for s in stmt.body:
            self._build_statement(s)

    def _build_call(self, stmt):
        for arg in stmt.args:
            self._build_expression(arg)

    def _build_expression(self, expr):
        from ir import IRType, IROpcode
        if isinstance(expr, Literal):
            return self.emit_constant(expr.value, self._literal_type(expr), 0)
        elif isinstance(expr, Identifier):
            return self.emit_load(expr.name, IRType.UNKNOWN, 0)
        elif isinstance(expr, BinaryOp):
            left_temp = self._build_expression(expr.left)
            right_temp = self._build_expression(expr.right)
            result_temp = self.new_temp()
            self.emit_binary_op(self._op_to_str(expr.op), left_temp, right_temp, result_temp, IRType.UNKNOWN, 0)
            return result_temp
        elif isinstance(expr, UnaryOp):
            operand_temp = self._build_expression(expr.expr)
            result_temp = self.new_temp()
            self.emit_unary_op(self._op_to_str(expr.op), operand_temp, result_temp, IRType.UNKNOWN, 0)
            return result_temp
        elif isinstance(expr, Call):
            args = []
            for arg in expr.args:
                args.append(self._build_expression(arg))
            result_temp = self.new_temp()
            qualified_name = self._qualified_name(expr.name)
            self.emit_call(qualified_name, args, result_temp, IRType.UNKNOWN, 0)
            return result_temp
        elif isinstance(expr, Indexing):
            target_temp = self._build_expression(expr.target)
            if not expr.index:
                raise KoCompileError("Indexing requires at least one index expression", 0, 0)
            for idx_expr in expr.index:
                index_temp = self._build_expression(idx_expr)
                result_temp = self.new_temp()
                self.emit_binary_subscr(target_temp, index_temp, result_temp, IRType.UNKNOWN, 0)
                target_temp = result_temp
            return result_temp
        elif isinstance(expr, TupleLiteral):
            result_temp = self.new_temp()
            element_temps = []
            for elem in expr.elements:
                element_temps.append(self._build_expression(elem))
            self.emit(IROpcode.BUILD_TUPLE, element_temps, len(element_temps), result_temp, IRType.TUPLE, 0)
            return result_temp
        elif isinstance(expr, DictLiteral):
            result_temp = self.new_temp()
            kv_temps = []
            for k, v in expr.mapping.items():
                kv_temps.append(self._build_expression(k))
                kv_temps.append(self._build_expression(v))
            self.emit(IROpcode.BUILD_MAP, kv_temps, len(kv_temps) // 2, result_temp, IRType.DICT, 0)
            return result_temp
        return None

    def _op_to_str(self, op):
        op_map = {
            TokenType.PLUS: "+", TokenType.MINUS: "-", TokenType.STAR: "*",
            TokenType.TILDE: "*", TokenType.SLASH: "/", TokenType.PERCENT: "%",
            TokenType.AND: "and", TokenType.OR: "or",
            TokenType.EQ: "==", TokenType.NE: "!=",
            TokenType.GT: ">", TokenType.GE: ">=", TokenType.LE: "<=",
            TokenType.LANGLE: "<"
        }
        return op_map.get(op, str(op))

    def _literal_type(self, expr):
        from ir import IRType
        if isinstance(expr.value, bool):
            return IRType.BOOL
        elif isinstance(expr.value, int):
            return IRType.INT
        elif isinstance(expr.value, float):
            return IRType.FREAL
        elif isinstance(expr.value, str):
            return IRType.STRING
        elif isinstance(expr.value, bytes):
            return IRType.BYTE
        return IRType.UNKNOWN

    def _type_name_to_ir_type(self, type_name):
        from ir import IRType
        if type_name is None:
            return IRType.UNKNOWN
        mapping = {
            "int": IRType.INT, "freal": IRType.FREAL, "string": IRType.STRING,
            "booling": IRType.BOOL, "byte": IRType.BYTE,
        }
        return mapping.get(type_name, IRType.UNKNOWN)

    def emit_unary_op(self, op, operand, result, ir_type=None, line=0):
        from ir import IRType, IROpcode
        if ir_type is None:
            ir_type = IRType.UNKNOWN
        self.emit(IROpcode.UNARY_OP, operand, None, result, ir_type, line, op=op)


def run_ko_source(source: str, file_name: str = "<stdin>", enable_optimization: bool = True) -> None:
    if len(source) > MAX_SOURCE_SIZE:
        raise KoCompileError(f"Source file exceeds maximum size of {MAX_SOURCE_SIZE} bytes")
    _validate_source_security(source, file_name)
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    parser = KoParser(tokens)
    program = parser.parse()

    if enable_optimization:
        from semantic_analyzer import SemanticAnalyzer
        from optimizer import Optimizer
        from ir import IRModule

        analyzer = SemanticAnalyzer()
        ir_module = analyzer.analyze(program)

        optimizer = Optimizer()
        ir_module = optimizer.optimize(ir_module)

    interpreter = KoInterpreter(program)
    try:
        interpreter.run()
    except KoCompileError:
        raise
    except ReturnException as e:
        pass
    except Exception as exc:
        raise KoCompileError(f"Runtime error: {exc}") from exc


def run_ko_source_with_ir(source: str, file_name: str = "<stdin>") -> Dict[str, Any]:
    if len(source) > MAX_SOURCE_SIZE:
        raise KoCompileError(f"Source file exceeds maximum size of {MAX_SOURCE_SIZE} bytes")
    _validate_source_security(source, file_name)
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    parser = KoParser(tokens)
    program = parser.parse()

    from semantic_analyzer import SemanticAnalyzer
    from optimizer import Optimizer
    from ir import ir_to_string

    analyzer = SemanticAnalyzer()
    ir_module = analyzer.analyze(program)

    ir_builder = IRBuilder()
    ir_module_from_ast = ir_builder.build(program)

    optimizer = Optimizer()
    ir_module_optimized = optimizer.optimize(ir_module_from_ast)

    return {
        "program": program,
        "ir_module": ir_module_optimized,
        "ir_text": ir_to_string(ir_module_optimized),
        "optimizer_report": optimizer.get_report(),
        "semantic_errors": analyzer.get_errors(),
        "semantic_warnings": analyzer.get_warnings(),
    }


def _validate_source_security(source: str, file_name: str) -> None:
    import hashlib
    lines = source.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("**Import**"):
            module_name = _extract_import_module(stripped)
            if module_name and module_name not in ALLOWED_MODULES:
                raise KoCompileError(f"Security violation: disallowed module '{module_name}' imported at line {i}", i, 0)
        if "file://" in stripped:
            raise KoCompileError(f"Security violation: file:// URLs are banned at line {i}", i, 0)
        if len(stripped) > 10000:
            raise KoCompileError(f"Line {i} exceeds maximum length of 10000 characters", i, 0)
        if _contains_dangerous_call(stripped) and not stripped.startswith("|"):
            raise KoCompileError(f"Security violation: dangerous function call at line {i}", i, 0)
        if _contains_os_path_traversal(stripped):
            raise KoCompileError(f"Security violation: path traversal detected at line {i}", i, 0)
        if _contains_banned_url_scheme(stripped):
            raise KoCompileError(f"Security violation: banned URL scheme at line {i}", i, 0)


def _extract_import_module(line: str) -> str:
    import re
    m = re.search(r'\$(\w+)\s*\)', line)
    return m.group(1) if m else None


def _contains_dangerous_call(line: str) -> bool:
    dangerous = ["exec(", "eval(", "__import__(", "subprocess", "os.system", "shutil", "pickle", "shelve"]
    return any(d in line for d in dangerous)


def _contains_os_path_traversal(line: str) -> bool:
    return ".." in line and ("Import" in line or "os.path" in line or "open" in line)


def _contains_banned_url_scheme(line: str) -> bool:
    for scheme in BANNED_URL_SCHEMES:
        if scheme + "://" in line:
            return True
    return False


def _is_safe_os_path(path: str) -> bool:
    if not path:
        return False
    if ".." in path:
        return False
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return any(path == sp or path.startswith(sp + "/") for sp in SAFE_OS_PATHS)


def run_ko_file(path: str) -> None:
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    run_ko_source(source, file_name=path)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run .ko source (v2.505)")
    parser.add_argument("source", help="Path to a .ko file")
    args = parser.parse_args(argv)
    if not args.source:
        parser.print_help()
        return 1
    if not os.path.exists(args.source):
        print(f"File not found: {args.source}", file=sys.stderr)
        return 1
    try:
        run_ko_file(args.source)
    except KoCompileError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
