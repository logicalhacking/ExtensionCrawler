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

class ParserState(Enum):
    """Enumeration of the possible parser states."""
    CODE = 1
    SINGLE_LINE_COMMENT = 2
    MULTI_LINE_COMMENT = 3
    STRING_SQ = 4
    STRING_DQ = 5


def is_string_literal_sq(state):
    return state == ParserState.STRING_SQ


def is_string_literal_dq(state):
    return state == ParserState.STRING_DQ


def is_string_literal(state):
    return is_string_literal_sq(state) or is_string_literal_dq(state)


def is_code(state):
    return state == ParserState.CODE


def is_code_or_string_literal(state):
    return is_code(state) or is_string_literal(state)


def is_comment_multi_line(state):
    return state == ParserState.MULTI_LINE_COMMENT


def is_comment_single_line(state):
    return state == ParserState.SINGLE_LINE_COMMENT


def is_comment(state):
    return is_comment_single_line(state) or is_comment_multi_line(state)


def get_next_character(fileobj):
    """Reads one character from the given textfile"""
    char = fileobj.read(1)
    while char:
        yield char
        char = fileobj.read(1)


def mince_js(file):
    with open(file, encoding="utf-8") as fileobj:
        line = 0
        cpos = 0
        escaped = False
        block_buffer = ""
        block_start_line = 0
        block_start_cpos = 0
        state = ParserState.CODE

        for char in get_next_character(fileobj):
            cpos += 1
            suc_state = state
            if not escaped:
                if is_code_or_string_literal(state):
                    if is_code(state):
                        if char == "'":
                            suc_state = ParserState.STRING_SQ
                        if char == '"':
                            suc_state = ParserState.STRING_DQ
                        if char == '/':
                            next_char = next(get_next_character(fileobj))
                            if next_char == '/':
                                suc_state = ParserState.SINGLE_LINE_COMMENT
                            elif next_char == '*':
                                suc_state = ParserState.MULTI_LINE_COMMENT
                            char = char + next_char
                            cpos += 1
                    elif is_string_literal_dq(state):
                        if char == '"':
                            suc_state = ParserState.CODE
                    elif is_string_literal_sq(state):
                        if char == "'":
                            suc_state = ParserState.CODE
                    else:
                        raise Exception("Unknown state")
                elif is_comment(state):
                    if is_comment_single_line(state):
                        if char == '\n':
                            suc_state = ParserState.CODE
                    elif is_comment_multi_line(state):
                        if char == '*':
                            next_char = next(get_next_character(fileobj))
                            if next_char == '/':
                                suc_state = ParserState.CODE
                            char = char + next_char
                            cpos += 1

            print(char, sep="", end="")
            if char == '\n':
                print(str(line) + ": ", end='')
                line += 1
                cpos = 0

            escaped = bool(char == '\\' and not escaped)

            state = suc_state
