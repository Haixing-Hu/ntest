#!/usr/bin/python
from __future__ import print_function

import argparse
import collections
import re
import subprocess
import sys


import basic_asm

DISASSEMBLER = ["objdump", "-d", "-C",  "--no-show-raw-insn"]

FUNC_START_RE = re.compile("\s*[0-9a-f]+\s+<(.*)>:")

def ProcessFuncLines(func, lines, show_dis):
    print(func)
    if show_dis:
        for line in lines:
            print(line)
        print()
    line_errors = 0
    branches = 0
    stores = 0
    stack_stores = 0
    loads = 0
    stack_loads = 0
    moves = 0
    alu_ops = 0
    mults = 0
    popcnts = 0
    total_count = 0
    unhandled_opcodes = set()
    for line in lines:
        if line != "": 
            insn = basic_asm.parse('instruction', line)
            if insn is None:
                print >> sys.stderr, "Parse error for ", line
                line_errors += 1
            if insn.opcode.startswith("nop") or insn.opcode == "retq":
                continue
            elif insn.opcode in [ "jmp", "jne", "jnz", "ja", "jb", "je", "jmpq", "callq"]:
                branches += 1
            elif insn.opcode.startswith("mov"):
                assert len(insn.params) == 2
                p1 = insn.params[0] 
                p2 = insn.params[1]
                if p1.addr is not None: 
                    # we got a load
                    assert p2.addr is None
                    if p1.addr.is_stack_based():
                        stack_loads += 1
                    else:
                        loads += 1
                elif p2.addr is not None:
                    # we got a store
                    assert p1.addr is None
                    if p2.addr.is_stack_based():
                        stack_stores += 1
                    else:
                        stores += 1
                else:
                    moves += 1
            elif insn.opcode == "pop":
                stack_loads += 1
            elif insn.opcode == "push":
                stack_stores += 1
            elif insn.opcode == "lea":
                alu_ops += 1
            elif insn.opcode == "test":
                alu_ops += 1
                assert len(insn.params) == 2
                for p in insn.params:
                    if p.addr is not None:
                        total_count += 1
                        if p.addr.is_stack_based():
                            stack_loads += 1
                        else:
                            loads += 1
            elif insn.opcode in ["and", "or", "xor", "shr", "shl", "sar", "add", "sub", "not"]:
                alu_ops += 1
                if len(insn.params) == 1:
                    assert insn.params[0].addr is None
                elif len(insn.params) == 2:
                    p1 = insn.params[0] 
                    p2 = insn.params[1]
                    if p1.addr is not None:
                        assert p2.addr is None
                        total_count += 1
                        if p1.addr.is_stack_based():
                            stack_loads += 1
                        else:
                            loads += 1
                    elif p2.addr is not None:
                        assert p1.addr is None
                        total_count += 1
                        if p2.addr.is_stack_based():
                            stack_stores += 1
                        else:
                            stores += 1
            elif insn.opcode == "popcnt":
                popcnts += 1
            elif insn.opcode in ["mul", "imul"]:
                mults += 1
            else:
                unhandled_opcodes.add(insn.opcode)
            total_count += 1
    for header in ["Total", "Branches", "stores", "st stores", "loads", "st loads", "moves", "alu", "mult", "popcnt"]:
        print("%10s" % header, end=" ")
    print()
    for count in [total_count, branches, stores, stack_stores, loads, stack_loads, moves, alu_ops, mults, popcnts]:
        print("%10d" % count, end=" ")
    print()
    if len(unhandled_opcodes) > 0:
        print("WARNING: there are unhandled opcodes:", " ".join(unhandled_opcodes), file=sys.stderr)

def HandleFunction(filename, funcname, show_dis):
    dis_subproc = subprocess.Popen(DISASSEMBLER + [filename], stdout = subprocess.PIPE, stderr = None)
    last_func = None
    good_lines = []

    for line in dis_subproc.stdout:
        line = line.decode('utf-8').strip()
        match = FUNC_START_RE.match(line)
        if match is not None:
            line_func_name = match.group(1)
            if last_func is not None:
                ProcessFuncLines(last_func, good_lines, show_dis)
            good_lines = []
            if line_func_name.startswith(funcname + "("):
                last_func = line_func_name
            else:
                last_func = None
        else:
            if last_func is not None:
                good_lines.append(line)


    exit_code = dis_subproc.wait()
    if exit_code != 0:
        print >> sys.stderr, "Disassembler command failed with code", exit_code
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser("Disassembly inspector")
    parser.add_argument("filename")
    parser.add_argument("funcname")
    parser.add_argument("-d", "--dis", action="store_true", default=False)
    args = parser.parse_args()
    HandleFunction(args.filename, args.funcname, args.dis)

if __name__ == "__main__":
    main()
