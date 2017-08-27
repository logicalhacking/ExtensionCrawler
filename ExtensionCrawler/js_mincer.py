#!/usr/bin/env python3
#
# Copyright (C) 2016,2017 The University of Sheffield, UK
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
""" A mostly correct JavaScript analyser that separted comments from code. The
    implementation priotizes speed over correctness. """

from enum import Enum


class JsBlockType(Enum):
    """Enumeration of the different JavaScript blocks."""
    CODE_BLOCK = 1
    SINGLE_LINE_COMMENT = 2
    SINGLE_LINE_COMMENT_BLOCK = 3
    MULTI_LINE_COMMENT_BLOCK = 4
    STRING_SQ = 5
    STRING_DQ = 6


def is_string_literal_sq(state):
    """Check if block is a single quote tring literal."""
    return state == JsBlockType.STRING_SQ


def is_string_literal_dq(state):
    """Check if block is a double quote tring literal."""
    return state == JsBlockType.STRING_DQ


def is_string_literal(state):
    """Check if block is a quote tring literal."""
    return is_string_literal_sq(state) or is_string_literal_dq(state)


def is_code(state):
    """Check if block is code (without string literals)."""
    return state == JsBlockType.CODE_BLOCK


def is_code_or_string_literal(state):
    """Check if block is code or a string literal."""
    return is_code(state) or is_string_literal(state)


def is_comment_multi_line(state):
    """Check if block is a multi line comment."""
    return state == JsBlockType.MULTI_LINE_COMMENT_BLOCK


def is_comment_single_line(state):
    """Check if block is a single line comment."""
    return state == JsBlockType.SINGLE_LINE_COMMENT


def is_comment(state):
    """Check if block is a comment."""
    return is_comment_single_line(state) or is_comment_multi_line(state)


def get_next_character(fileobj):
    """Get next character from (text) file."""
    char = fileobj.read(1)
    while char:
        yield char
        char = fileobj.read(1)


class JsBlock:
    """Class representing JavaScript blocks."""

    def __init__(self, typ, start, end, content, string_literals=None):
        self.typ = typ
        self.start = start
        self.end = end
        self.content = content
        self.string_literals = string_literals

    def is_code(self):
        """Check if block is a code block."""
        is_code(self.typ)

    def is_comment(self):
        """Check if block is a comment."""
        is_comment(self.typ)

    def __str__(self):
        str_msg = ""
        if is_code(self.typ):
            str_msg = "** String Literals: " + str(
                len(self.string_literals)) + "\n"
        return (
            "***************************************************************\n"
            + "** Type:  " + str(self.typ) + "\n" + "** Start: " + str(
                self.start) + "\n" + "** End:   " + str(
                    self.end) + "\n" + str_msg + self.content.strip() + "\n" +
            "***************************************************************\n"
        )


def mince_js_fileobj(fileobj):
    """Mince JavaScript file object into code and comment blocks."""
    line = 0
    cpos = 0
    escaped = False
    content = ""
    block_start_line = 0
    block_start_cpos = 0
    state = JsBlockType.CODE_BLOCK
    string_literals = []
    current_string_literal = ""

    for char in get_next_character(fileobj):
        cpos += 1
        content += char
        suc_state = state
        if not escaped:
            if is_code_or_string_literal(state):
                if is_code(state):
                    if char == "'":
                        suc_state = JsBlockType.STRING_SQ
                    if char == '"':
                        suc_state = JsBlockType.STRING_DQ
                    if char == '/':
                        next_char = next(get_next_character(fileobj))
                        if next_char == '/':
                            suc_state = JsBlockType.SINGLE_LINE_COMMENT
                        elif next_char == '*':
                            suc_state = JsBlockType.MULTI_LINE_COMMENT_BLOCK
                        next_content = content[-1] + next_char
                        content = content[:-1]
                        cpos -= 1
                elif is_string_literal_dq(state):
                    if char == '"':
                        suc_state = JsBlockType.CODE_BLOCK
                        string_literals.append(current_string_literal)
                        current_string_literal = ""
                    else:
                        current_string_literal += char
                elif is_string_literal_sq(state):
                    if char == "'":
                        suc_state = JsBlockType.CODE_BLOCK
                        string_literals.append(current_string_literal)
                        current_string_literal = ""
                    else:
                        current_string_literal += char
                else:
                    raise Exception("Unknown state")
            elif is_comment(state):
                if is_comment_single_line(state):
                    if char == '\n':
                        suc_state = JsBlockType.CODE_BLOCK
                elif is_comment_multi_line(state):
                    if char == '*':
                        next_char = next(get_next_character(fileobj))
                        if next_char == '/':
                            suc_state = JsBlockType.CODE_BLOCK
                        content = content + next_char
                        cpos += 1

        if ((is_comment(state) and is_code_or_string_literal(suc_state)) or
                (is_code_or_string_literal(state) and is_comment(suc_state))):
            yield (JsBlock(state, (block_start_line, block_start_cpos),
                           (line, cpos), content, string_literals))
            block_start_line = line
            block_start_cpos = cpos + len(next_content)
            content = next_content
            next_content = ""
            string_literals = []

        if char == '\n':
            line += 1
            cpos = 0

        escaped = bool(char == '\\' and not escaped)
        state = suc_state


def mince_js(file):
    """Mince JavaScript file into code and comment blocks."""
    with open(file, encoding="utf-8") as fileobj:
        for block in mince_js_fileobj(fileobj):
            yield block
