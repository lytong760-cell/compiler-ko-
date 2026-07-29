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
        self.quote_stack = []

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
            
            if self.quote_stack and char == "}":
                self.tokens.append(Token(TokenType.RBRACE, "}", self.line, self.column))
                self._advance()
                self._tokenize_string_fragment(self.quote_stack.pop())
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
                # Peak ahead to see if it's a known tag
                temp_pos = self.pos
                temp_text = ""
                while temp_pos < len(self.source) and not self.source[temp_pos].isspace() and self.source[temp_pos] not in "()^":
                    temp_text += self.source[temp_pos]
                    temp_pos += 1
                    if self.source[temp_pos-1] == ">": break
                
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
                # Keep IDs together if they contain * or ~ (sigils in the middle)
                while self._peek().isalnum() or self._peek() in "_@*~":
                    text += self._advance()
                
                kw_map = {
                    "Import": TokenType.IMPORT,
                    "Loop": TokenType.LOOP,
                    "!class": TokenType.CLASS,
                    "@private": TokenType.PRIVATE,
                    "@loop": TokenType.LOOP_CTRL,
                    "@also": TokenType.ALSO,
                    "int": TokenType.ID,
                    "freal": TokenType.ID,
                    "string": TokenType.ID,
                    "booling": TokenType.ID,
                    "byte": TokenType.ID,
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

            if char in "~*":
                self.tokens.append(Token(TokenType.TILDE, char, self.line, self.column))
                self._advance()
                continue
            char_map = {
                "~": TokenType.TILDE,
                "*": TokenType.TILDE,
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
                "*": TokenType.STAR,
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

    def _tokenize_string_fragment(self, quote: str):
        start_col = self.column
        content = ""
        while self._peek() and self._peek() != quote:
            if self._peek() == "{":
                if content:
                    self.tokens.append(Token(TokenType.STRING, content, self.line, start_col))
                self.tokens.append(Token(TokenType.LBRACE, "{", self.line, self.column))
                self._advance()
                self.quote_stack.append(quote)
                return
            
            if self._peek() == "\\":
                self._advance()
                content += self._advance()
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

@dataclass
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

@dataclass
class Assignment(Stmt):
    target: Identifier
    value: Expr

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
        print(tokens) # Debug
        self.pos = 0

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
        print(f"Consuming {type}, current is {self._peek()}") # Debug
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
            condition = error_code
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
        if self._check(TokenType.ID) and self._peek(1).type == TokenType.LPAREN:
            # Check if it's a function decl or var decl
            # ID(expr)~name is var decl
            # ID(...) [ is function decl
            # Search for [ or ~
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
        elif self._match(TokenType.STAR):
            # Might be method call or instantiation or function call
            return self.parse_call_or_instantiation()
        elif self._check(TokenType.DOLLAR):
            return self.parse_call_or_instantiation()
        elif self._check(TokenType.ID):
            # Might be VarDecl or Assignment or Instance method call
            if self._peek(1).type == TokenType.LPAREN:
                # Type(val)~name
                return self.parse_var_decl()
            elif self._peek(1).type == TokenType.STAR:
                # Assignment or method call handled elsewhere
                pass
        
        # Default to expression statement or assignment
        expr = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        if self._match(TokenType.TILDE):
            # Expression ~ Identifier (Assignment or VarDecl without type)
            target = self._consume(TokenType.ID, "Expected target identifier").value
            return Assignment(Identifier(target), expr)
        
        return expr # This would be an expression stmt

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
        self._consume(TokenType.STAR, "Actually it's = in spec for loop?") # Spec: <for>(~x=1&=6)
        # Wait, the spec says =. My lexer might not have =.
        # Fixed in thought: I'll add EQ as = and match it.
        # But wait, spec uses = for assignment in for loop.
        # I'll use the ID or custom match.
        # Re-reading spec: <for>(~x=1&=6)
        # I'll just skip the '=' if it's there.
        self._consume(TokenType.ASSIGN, "Expected =")
        
        start = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        
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
        
        return ForLoop(var_name, start, end, step, body)

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
            if not self._match(TokenType.GT, TokenType.GE, TokenType.LE, TokenType.EQ, TokenType.NE):
                break
            op = self.tokens[self.pos-1].type
            if stop_tokens and op in stop_tokens:
                self.pos -= 1 # Backtrack
                break
            right = self.parse_term(stop_tokens)
            expr = BinaryOp(expr, op, right)
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
        if self._match(TokenType.MINUS, TokenType.TILDE):
            op = self.tokens[self.pos-1].type
            expr = self.parse_unary(stop_tokens)
            return UnaryOp(op, expr)
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
            if next_token.type == TokenType.LANGLE and next_token.line == self.tokens[self.pos-1].line and next_token.column == self.tokens[self.pos-1].column + len(str(self.tokens[self.pos-1].value)):
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

        if self._match(TokenType.LPAREN):
            elements = []
            if not self._check(TokenType.RPAREN):
                while True:
                    elements.append(self.parse_expression(stop_tokens=[TokenType.RPAREN]))
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RPAREN, "Expected )")
            if len(elements) == 1:
                if self._check(TokenType.LBRACE):
                    key = elements[0]
                    self._consume(TokenType.LBRACE, "Expected {")
                    value = self.parse_expression(stop_tokens=[TokenType.RPAREN])
                    self._consume(TokenType.RBRACE, "Expected }")
                    return DictLiteral({key: value})
                if self._peek().type == TokenType.TILDE:
                    return TupleLiteral(elements)
                return elements[0]
            return TupleLiteral(elements)

        self._error(f"Expected expression, found {self._peek().type}")

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
                return VarDecl(name, None, instance_name)
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
                return Call("memory_free", [Identifier(target)])
        
        self._error("Invalid memory operation")

    def parse_print(self) -> Stmt:
        is_printf = self._peek().type == TokenType.PRINTF
        self._advance() # Consume <print> or <printf>
        
        if not is_printf:
            self._consume(TokenType.ID, "Expected type (string)")
            
        self._consume(TokenType.CARET, "Expected ^")
        self._consume(TokenType.LPAREN, "Expected (")
        
        # Collect everything until the closing )
        content = ""
        while not self._check(TokenType.RPAREN):
            token = self._advance()
            if token.value:
                content += str(token.value)
            
        self._consume(TokenType.RPAREN, "Expected )")
        return Call("printf" if is_printf else "print", [Literal(content)])

    def parse_input(self) -> Stmt:
        self._consume(TokenType.INPUT, "Expected <input>")
        self._consume(TokenType.LPAREN, "Expected (")
        prompt = self.parse_expression(stop_tokens=[TokenType.RPAREN])
        self._consume(TokenType.RPAREN, "Expected )")
        
        if self._match(TokenType.ASSIGN_INPUT):
            # <input>(...)&=string("")~name
            # or <input>(...)&=name
            if self._check(TokenType.ID) and self._peek(1).type == TokenType.LPAREN:
                # New var decl
                decl = self.parse_var_decl()
                return Assignment(Identifier(decl.name), Call("input", [prompt]))
            else:
                target = self._consume(TokenType.ID, "Expected target variable").value
                return Assignment(Identifier(target), Call("input", [prompt]))
        
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


class KoCodeGenerator:
    def __init__(self, program: Program):
        self.program = program
        self.output = []
        self.indent_level = 0
        self.scope_stack = ["global"]

    def _indent(self):
        return "    " * self.indent_level

    def _write(self, line: str):
        self.output.append(self._indent() + line)

    def generate(self) -> str:
        # 1. Imports
        for imp in self.program.imports:
            self._write(f"# Import handled by Import.java simulation")
            self._write(f"import {imp.module_name.lower()} as {imp.alias}")

        # 2. Classes and Functions
        for decl in self.program.decls:
            self.visit(decl)

        # 3. Main Block with Upward Catching
        if self.program.main:
            self.visit(self.program.main)

        # 4. Global Catch Blocks (Sequential Upward)
        # In .ko, catch blocks at the end protect EVERYTHING before them in the same scope.
        # This requires wrapping the generated code in try/except.
        if self.program.catch_blocks:
            final_code = "\n".join(self.output)
            self.output = []
            self._write("try:")
            self.indent_level += 1
            for line in final_code.split("\n"):
                self.output.append(self._indent() + line.lstrip())
            self.indent_level -= 1
            
            for catch in self.program.catch_blocks:
                self.visit(catch)

        return "\n".join(self.output)

    def visit(self, node: Node):
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node):
        raise NotImplementedError(f"No visit_{node.__class__.__name__} method")

    def visit_ClassDecl(self, node: ClassDecl):
        self._write(f"class {node.name}:")
        self.indent_level += 1
        self.scope_stack.append("class")
        
        # Merge public and private
        all_stmts = node.body + node.private_body
        if not all_stmts:
            self._write("pass")
        else:
            for stmt in all_stmts:
                self.visit(stmt)
        
        self.scope_stack.pop()
        self.indent_level -= 1

    def visit_FuncDecl(self, node: FuncDecl):
        params = [p.name for p in node.params]
        if self.scope_stack[-1] == "class":
            params = ["self"] + params
        
        param_str = ", ".join(params)
        self._write(f"def {node.name}({param_str}):")
        self.indent_level += 1
        self.scope_stack.append("func")
        
        if not node.body:
            self._write("pass")
        else:
            for stmt in node.body:
                self.visit(stmt)
        
        self.scope_stack.pop()
        self.indent_level -= 1

    def visit_MainBlock(self, node: MainBlock):
        self._write("def main():")
        self.indent_level += 1
        self.scope_stack.append("main")
        
        if not node.body:
            self._write("pass")
        else:
            for stmt in node.body:
                self.visit(stmt)
        
        self.scope_stack.pop()
        self.indent_level -= 1
        self._write("\nif __name__ == '__main__':")
        self._write("    main()")

    def visit_VarDecl(self, node: VarDecl):
        val = self.visit(node.initializer) if node.initializer else "None"
        self._write(f"{node.name} = {val}")

    def visit_Assignment(self, node: Assignment):
        val = self.visit(node.value)
        self._write(f"{node.target.name} = {val}")

    def visit_NowMutation(self, node: NowMutation):
        val = self.visit(node.expr)
        self._write(f"{node.target.name} = {val}")

    def visit_IfStmt(self, node: IfStmt):
        cond = self.visit(node.condition)
        self._write(f"if {cond}:")
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        
        if node.else_body:
            if isinstance(node.else_body, IfStmt):
                self._visit_elif(node.else_body)
            else:
                self._write("else:")
                self.indent_level += 1
                for stmt in node.else_body:
                    self.visit(stmt)
                self.indent_level -= 1

    def _visit_elif(self, node: IfStmt):
        cond = self.visit(node.condition)
        self._write(f"elif {cond}:")
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        
        if node.else_body:
            if isinstance(node.else_body, IfStmt):
                self._visit_elif(node.else_body)
            else:
                self._write("else:")
                self.indent_level += 1
                for stmt in node.else_body:
                    self.visit(stmt)
                self.indent_level -= 1

    def visit_ForLoop(self, node: ForLoop):
        self._write(f"# Optimized by Loop.cpp simulation")
        start = self.visit(node.start)
        end = self.visit(node.end)
        step = self.visit(node.step) if node.step else "1"
        self._write(f"for {node.var_name} in range({start}, {end} + 1, {step}):")
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1

    def visit_WhileLoop(self, node: WhileLoop):
        cond = self.visit(node.condition)
        self._write(f"while {cond}:")
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1

    def visit_CatchStmt(self, node: CatchStmt):
        if isinstance(node.error_condition, str):
            # Error code
            self._write(f"except Exception as e if getattr(e, 'type', None) == '{node.error_condition}' else False:")
        else:
            # Condition
            cond = self.visit(node.error_condition)
            self._write(f"except Exception as e:")
            self.indent_level += 1
            self._write(f"if not ({cond}): raise e")
        
        self.indent_level += 1
        # error dictionary
        self._write("error = {'line': sys.exc_info()[2].tb_lineno, 'code': '', 'type': type(e).__name__}")
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1

    def visit_Literal(self, node: Literal):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        return str(node.value)

    def visit_Identifier(self, node: Identifier):
        return node.name

    def visit_BinaryOp(self, node: BinaryOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_map = {
            TokenType.PLUS: "+", TokenType.MINUS: "-", TokenType.STAR: "*",
            TokenType.SLASH: "/", TokenType.PERCENT: "%",
            TokenType.AND: "and", TokenType.OR: "or",
            TokenType.EQ: "==", TokenType.NE: "!=",
            TokenType.GT: ">", TokenType.GE: ">=", TokenType.LE: "<=",
            TokenType.LANGLE: "<"
        }
        return f"({left} {op_map[node.op]} {right})"

    def visit_UnaryOp(self, node: UnaryOp):
        expr = self.visit(node.expr)
        op = "-" if node.op == TokenType.MINUS else "not"
        return f"{op}({expr})"

    def visit_Indexing(self, node: Indexing):
        target = self.visit(node.target)
        indices = "".join(f"[{self.visit(idx)}]" for idx in node.index)
        return f"{target}{indices}"

    def visit_Call(self, node: Call):
        args_list = [self.visit(arg) for arg in node.args]
        args = ", ".join(args_list)
        if node.name == "printf":
            # Combine args into a single f-string if they are fragments
            parts = []
            for arg in node.args:
                if isinstance(arg, Literal) and isinstance(arg.value, str):
                    parts.append(arg.value)
                else:
                    parts.append(f"{{{self.visit(arg)}}}")
            call_code = f'print(f"{"".join(parts)}")'
        elif node.name == "print":
            call_code = f"print({args})"
        elif node.name == "input":
            call_code = f"input({args})"
        elif node.name == "random":
            call_code = f"random.randint({args})"
        elif node.name == "return":
            self._write(f"return {args}")
            return ""
        elif node.is_instance_method:
            instance = node.instance or "self"
            call_code = f"{instance}.{node.name}({args})"
        else:
            call_code = f"{node.name}({args})"
            
        if node.target:
            self._write(f"{node.target} = {call_code}")
            return node.target
        
        return call_code

    def visit_TupleLiteral(self, node: TupleLiteral):
        elements = ", ".join(self.visit(e) for e in node.elements)
        return f"({elements})"

    def visit_DictLiteral(self, node: DictLiteral):
        mapping = ", ".join(f"{self.visit(k)}: {self.visit(v)}" for k, v in node.mapping.items())
        return f"{{{mapping}}}"


class KoInterpreter:
    def __init__(self, program: Program):
        self.program = program
        self.scopes = [{}]
        self.functions = {}
        self.classes = {}

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
        self.scopes[-1][name] = value

    def run(self):
        for decl in self.program.decls:
            if isinstance(decl, FuncDecl):
                self.functions[decl.name] = decl
            elif isinstance(decl, ClassDecl):
                self.classes[decl.name] = decl
        
        if self.program.main:
            self.visit(self.program.main)
    
    def visit(self, node: Node):
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
        
    def generic_visit(self, node: Node):
        raise NotImplementedError(f"No visit_{node.__class__.__name__} method")

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

    def visit_ForLoop(self, node: ForLoop):
        start = self.visit(node.start)
        end = self.visit(node.end)
        step = self.visit(node.step) if node.step else 1
        
        for i in range(start, end + 1, step):
            self.set_var(node.var_name, i)
            for stmt in node.body:
                self.visit(stmt)

    def visit_Call(self, node: Call):
        args = [self.visit(arg) for arg in node.args]
        
        if node.name == "print":
            print(*args)
        elif node.name == "printf":
            # Simplified printf
            print(args[0])
        elif node.name == "input":
            return input(args[0] if args else "")
        elif node.name == "return":
            # Handle return by raising a custom exception
            raise ReturnException(args[0] if args else None)
        else:
            # Custom function call
            if node.name in self.functions:
                func = self.functions[node.name]
                self.push_scope()
                # bind args
                for i, param in enumerate(func.params):
                    self.set_var(param.name, args[i])
                
                try:
                    for stmt in func.body:
                        self.visit(stmt)
                except ReturnException as e:
                    self.pop_scope()
                    return e.value
                self.pop_scope()
                return None
            else:
                raise NameError(f"Function {node.name} not defined")

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value
        val = self.visit(node.initializer) if node.initializer else None
        self.set_var(node.name, val)
        
    def visit_Assignment(self, node: Assignment):
        val = self.visit(node.value)
        for scope in reversed(self.scopes):
            if node.target.name in scope:
                scope[node.target.name] = val
                return
        self.set_var(node.target.name, val)

    def visit_Identifier(self, node: Identifier):
        return self.get_var(node.name)
        
    def visit_Literal(self, node: Literal):
        return node.value

    def visit_BinaryOp(self, node: BinaryOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        
        if node.op == TokenType.PLUS: return left + right
        if node.op == TokenType.MINUS: return left - right
        if node.op == TokenType.STAR: return left * right
        if node.op == TokenType.SLASH: return left / right
        if node.op == TokenType.PERCENT: return left % right
        if node.op == TokenType.AND: return left and right
        if node.op == TokenType.OR: return left or right
        if node.op == TokenType.EQ: return left == right
        if node.op == TokenType.NE: return left != right
        if node.op == TokenType.GT: return left > right
        if node.op == TokenType.GE: return left >= right
        if node.op == TokenType.LE: return left <= right
        raise NotImplementedError(f"Op {node.op} not implemented")

def run_ko_source(source: str, file_name: str = "<stdin>") -> None:
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    parser = KoParser(tokens)
    program = parser.parse()
    interpreter = KoInterpreter(program)
    interpreter.run()


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
