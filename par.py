import llvm.core
import ast

def init():
    module = llvm.core.Module.new("mod")

    # void fun (void)
    func_type = llvm.core.Type.function(llvm.core.Type.void(),
                                        [ llvm.core.Type.void() ])

    fun = llvm.core.Function.new (module, func_type, "fun")
    fun = CC_C

    #new block
    block = fun.append_basic_block("entry")

    #IR builder
    builder = llvm.core.Builder.new(block)

    return module, fun, block, builder


source = """
a = 1 + b
a = a + 1
a += 1
a /= a
"""


module, fun, block, builder = init()
print(module)

tree = ast.parse(source)
for node in tree.body:
    op = ""
    target, left, right = None, None, None
    if isinstance(node, ast.Assign):
        if isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
        else:
            pass

        if isinstance(node.value.left, ast.Num):
            left = node.value.left.n
        elif isinstance(node.value.left, ast.Name):
            left = node.value.left.id
        else:
            pass

        if isinstance(node.value.right, ast.Num):
            right = node.value.right.n
        elif isinstance(node.value.right, ast.Name):
            right = node.value.right.id
        else:
            pass

        if isinstance(node.value.op, ast.Add):
            op = "Add"
            #builder.add(left, right, target)
        elif isinstance(node.value.left, ast.Sub):
            op = "Sub"
        elif isinstance(node.value.left, ast.Mult):
            op = "Mult"
        elif isinstance(node.value.left, ast.Div):
            op = "Div"
        else:
            pass

        print("{} = {} {}, {}".format(target, op, left, right))

    elif isinstance(node, ast.AugAssign):
        if isinstance(node.target, ast.Name):
            target = node.target.id
        else:
            pass

        if isinstance(node.op, ast.Add):
            op = "Add"
        elif isinstance(node.op, ast.Sub):
            op = "Sub"
        elif isinstance(node.op, ast.Mult):
            op = "Mult"
        elif isinstance(node.op, ast.Div):
            op = "Div"
        else:
            pass

        if isinstance(node.value, ast.Num):
            right = node.value.n
        elif isinstance(node.value, ast.Name):
            right = node.value.id
        else:
            pass

        print("{} = {} {}, {}".format(target, op, target, right))

    else:
        print(ast.dump(node))
        print("unknown node")
