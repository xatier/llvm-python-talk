#!/usr/bin/env python

import ast
import ctypes

import llvmlite.ir
import llvmlite.binding


# source code
#
# two variables a and b (int32)
#
# support syntax:  op in + - * /
#     z = x op y
#     x op= y
#

source = """
a += 1
a *= 2
a *= 2
a *= 2
a *= 2
a *= 2

b += 1
b += a
b -= a
b *= a
b /= a
b += 1

#b = a + b
#a = a + b
#b = a + b
#a = a + b
#b = a + b
#a = a + b
#b = a + b
"""

# llvm type alias
int32 = llvmlite.ir.IntType(32)
int64 = llvmlite.ir.IntType(64)
void = llvmlite.ir.VoidType()

# initialize them later
a = None
b = None


def init():
    global a
    global b

    # llvmlite initialization
    llvmlite.binding.initialize()
    llvmlite.binding.initialize_native_target()
    llvmlite.binding.initialize_native_asmprinter()

    # llvm module
    module = llvmlite.ir.Module("mod")

    # void func (void)
    func_ty = llvmlite.ir.FunctionType(void, ())
    func = llvmlite.ir.Function(module, func_ty, name='func')

    # entry block
    block = func.append_basic_block('entry')

    # IR builder
    builder = llvmlite.ir.IRBuilder(block)

    # two variables
    a = builder.alloca(int32, name='a')
    b = builder.alloca(int32, name='b')
    zero = llvmlite.ir.Constant(int32, 0)
    builder.store(zero, a)
    builder.store(zero, b)

    # alright, now we have an LLVM module and two variables on the stack
    return module, builder


# emit LLVM IR from three address code notation
def inst(builder, op, left, right, target):
    global a
    global b

    assert op in ['Add', 'Sub', 'Mult', 'Div']
    assert target in ['a', 'b']
    assert isinstance(left, int) or left in ['a', 'b']
    assert isinstance(right, int) or right in ['a', 'b']

    # build constant objects for operands
    if isinstance(left, int):
        left = llvmlite.ir.Constant(int32, left)

    if isinstance(right, int):
        right = llvmlite.ir.Constant(int32, right)

    # load operands
    if left == 'a':
        left = builder.load(a)
    elif left == 'b':
        left = builder.load(b)

    if right == 'a':
        right = builder.load(a)
    elif right == 'b':
        right = builder.load(b)

    # emit operation
    if op == "Add":
        res = builder.add(left, right)
    elif op == "Sub":
        res = builder.sub(left, right)
    elif op == "Mult":
        res = builder.mul(left, right)
    elif op == "Div":
        res = builder.udiv(left, right)

    # store the result
    if target == 'a':
        builder.store(res, a)
    elif target == 'b':
        builder.store(res, b)


def compile_(source):

    module, builder = init()

    # Syntax directed translation!
    tree = ast.parse(source)

    for node in tree.body:
        # turn the syntax tree to three address code notation
        op = ""
        target, left, right = None, None, None

        if isinstance(node, ast.Assign):
            if isinstance(node.targets[0], ast.Name):
                target = node.targets[0].id

            if isinstance(node.value.left, ast.Num):
                left = node.value.left.n
            elif isinstance(node.value.left, ast.Name):
                left = node.value.left.id

            if isinstance(node.value.right, ast.Num):
                right = node.value.right.n
            elif isinstance(node.value.right, ast.Name):
                right = node.value.right.id

            if isinstance(node.value.op, ast.Add):
                op = "Add"
            elif isinstance(node.value.op, ast.Sub):
                op = "Sub"
            elif isinstance(node.value.op, ast.Mult):
                op = "Mult"
            elif isinstance(node.value.op, ast.Div):
                op = "Div"

            inst(builder, op, left, right, target)

        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                target = node.target.id

            if isinstance(node.op, ast.Add):
                op = "Add"
            elif isinstance(node.op, ast.Sub):
                op = "Sub"
            elif isinstance(node.op, ast.Mult):
                op = "Mult"
            elif isinstance(node.op, ast.Div):
                op = "Div"

            if isinstance(node.value, ast.Num):
                right = node.value.n
            elif isinstance(node.value, ast.Name):
                right = node.value.id

            inst(builder, op, target, right, target)

        else:
            # quit
            print(ast.dump(node))
            print("unknown node")
            import sys
            sys.exit(1)

    # dump the results

    # evil hacks here:
    #     1. wrap python function with ctypes
    #     2. get the function pointer (as int64)
    #     3. cast the function pointer to IR fun_ptr type
    #     4. call

    def dump(a, b):
        print('===========')
        print('a = {}'.format(a))
        print('b = {}'.format(b))
        print('===========')

    # void dump(int32, int32)
    py_func = ctypes.CFUNCTYPE(None, ctypes.c_int32, ctypes.c_int32)(dump)
    py_func_addr = ctypes.cast(py_func, ctypes.c_void_p).value

    # void (int32, int32)
    ir_func_ptr = llvmlite.ir.FunctionType(void, (int32, int32)).as_pointer()

    # cast dump to void (int32, int32)
    f = builder.inttoptr(llvmlite.ir.Constant(int64, py_func_addr),
                         ir_func_ptr, name='dump')

    # call
    builder.call(f, [builder.load(a), builder.load(b)])

    # function end
    builder.ret_void()
    return module


# main
if __name__ == '__main__':

    module = compile_(source)

    print('=== LLVM IR ===')
    print(module)

    # jit and run!
    llvm_module = llvmlite.binding.parse_assembly(str(module))
    tm = llvmlite.binding.Target.from_default_triple().create_target_machine()
    with llvmlite.binding.create_mcjit_compiler(llvm_module, tm) as ee:

        # finalize
        ee.finalize_object()
        # print('=== Assembly ===')
        # print(tm.emit_assembly(llvm_module))

        # run the jitted function
        cfptr = ee.get_pointer_to_function(llvm_module.get_function('func'))
        cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(cfptr)
        cfunc()
