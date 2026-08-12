import sys
import os
import time
import random
from ko_compiler import run_ko_source, KoCompileError

random.seed(42)

test_results = {"passed": 0, "failed": 0, "errors": 0, "total": 0}
failures = []

def make_test(name, source):
    test_results["total"] += 1
    try:
        run_ko_source(source, file_name=name)
        test_results["passed"] += 1
        return True
    except KoCompileError as e:
        test_results["failed"] += 1
        failures.append((name, str(e)))
        return False
    except Exception as e:
        test_results["errors"] += 1
        failures.append((name, f"{type(e).__name__}: {e}"))
        return False

tests = []

# Category 1: Basic arithmetic (from demo.ko patterns)
for i in range(1000):
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    c = a + b
    source = f"""
[
    int({a})~x
    int({b})~y
    int(x + y)~z
    <printf>^("Result: {{z}}\\n")
]
"""
    tests.append((f"basic_arith_{i}", source))

# Category 2: Variable declarations and assignments
for i in range(1000):
    var_type = random.choice(["int", "freal", "string", "booling"])
    val_map = {"int": "42", "freal": "3.14", "string": '"hello"', "booling": "\\True\\"}
    source = f"""
[
    {var_type}({val_map[var_type]})~v{i}
    <printf>^("Value: {{v{i}}}\\n")
]
"""
    tests.append((f"var_decl_{i}", source))

# Category 3: For loops (from demo.ko patterns)
for i in range(1000):
    start = random.randint(1, 5)
    end = start + random.randint(1, 10)
    step = random.choice([1, 2, 3])
    source = f"""
[
    **Loop** <for>(~i={start}({step})&={end}) [
        <printf>^("i={{i}}\\n")
    ]
]
"""
    tests.append((f"for_loop_{i}", source))

# Category 4: While loops
for i in range(1000):
    count = random.randint(1, 10)
    source = f"""
[
    int({count})~n
    @loop(n > 0)
    **Loop** <for.f.whle>@also [
        <printf>^("n={{n}}\\n")
        <now>(n - 1)>n
    ]
]
"""
    tests.append((f"while_loop_{i}", source))

# Category 5: If/elif/else
for i in range(1000):
    val = random.randint(1, 100)
    source = f"""
[
    int({val})~x
    <if>(x > 50) [
        <printf>^("Big\\n")
    ]
    <elif>(x > 25) [
        <printf>^("Medium\\n")
    ]
    <else> [
        <printf>^("Small\\n")
    ]
]
"""
    tests.append((f"if_elif_{i}", source))

# Category 6: Function calls
for i in range(1000):
    a = random.randint(1, 50)
    b = random.randint(1, 50)
    source = f"""
calculate(int~a, int~b) [
    int(a + b)~result
    <return>(result)
]
[
    int(~calculate({a}, {b}))~res
    <printf>^("Result: {{res}}\\n")
]
"""
    tests.append((f"func_call_{i}", source))

# Category 7: Class OOP
for i in range(1000):
    source = f"""
Hero !class [
    @private [
        int(100)~hp
        take_damage() [
            int(<$random>(10, 30))~dmg
            <now>(hp - dmg)>hp
            <return>(hp)
        ]
    ]
]
[
    ~Hero~h{i}
    int($h{i}~take_damage())~remaining
    <printf>^("HP: {{remaining}}\\n")
]
"""
    tests.append((f"class_oop_{i}", source))

# Category 8: Import statements
for i in range(1000):
    source = (
        "**Import**($Random)@also%~random" + str(i) + "!`global`:random" + str(i) + "\n"
        "[\n"
        "    int(<$random" + str(i) + ">(1, 100))~val" + str(i) + "\n"
        '    <printf>^("Random: {val' + str(i) + '}\\n")\n'
        "]\n"
    )
    tests.append((f"import_{i}", source))

# Category 9: String operations
for i in range(1000):
    source = f"""
[
    string("Hello .ko")~s{i}
    <printf>^("{{s{i}}}\\n")
]
"""
    tests.append((f"string_{i}", source))

# Category 10: Encoding operations
for i in range(1000):
    source = f"""
[
    bytes(<encode(`UTF-8`)^("Test {i}"))~enc{i}
    <printf>^("Encoded length: {{len(enc{i})}}\\n")
]
"""
    tests.append((f"encode_{i}", source))

# Category 11: Dictionary operations
for i in range(1000):
    source = f"""
[
    (1{{"a"}})~d{i}
    <printf>^("Dict value: {{d{i}<{{'a'}}>}}\\n")
]
"""
    tests.append((f"dict_{i}", source))

# Category 12: Tuple operations
for i in range(1000):
    source = f"""
[
    (1, 2, 3)~t{i}
    <printf>^("Tuple first: {{t{i}<0>}}\\n")
]
"""
    tests.append((f"tuple_{i}", source))

# Category 13: Memory operations
for i in range(1000):
    source = f"""
[
    int(999)~mem{i}
    <memory>dete(mem{i})
    <printf>^("Memory freed\\n")
]
"""
    tests.append((f"memory_{i}", source))

# Category 14: Catch blocks
for i in range(1000):
    source = f"""
safe_divide(int~a, int~b) [
    int(a / b)~result
    <return>(result)
    <catch>(`DivideByZeroError`) [
        <return>(0)
    ]
]
[
    int(~safe_divide(100, 0))~res
    <printf>^("Safe divide result: {{res}}\\n")
]
"""
    tests.append((f"catch_{i}", source))

# Category 15: Complex expressions
for i in range(1000):
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    c = random.randint(1, 20)
    source = f"""
[
    int(({a} + {b}) * {c})~result
    <printf>^("Complex: {{result}}\\n")
]
"""
    tests.append((f"complex_{i}", source))

# Category 16: Nested loops
for i in range(500):
    source = """
[
    **Loop** <for>(~i=1&=3) [
        **Loop** <for>(~j=1&=3) [
            <printf>^("i={i}, j={j}\\n")
        ]
    ]
]
"""
    tests.append((f"nested_loop_{i}", source))

# Category 17: Boolean logic
for i in range(1000):
    source = f"""
[
    booling(\\True\\)~b{i}
    booling(\\False\\)~f{i}
    <if>(b{i} && f{i} == \\False\\) [
        <printf>^("Bool logic works\\n")
    ]
]
"""
    tests.append((f"bool_logic_{i}", source))

# Category 18: Byte and bytes operations
for i in range(500):
    source = f"""
[
    byte("A")~b{i}
    bytes(8)~buf{i}
    <printf>^("Byte: {{b{i}}}\\n")
]
"""
    tests.append((f"byte_ops_{i}", source))

# Category 19: Now mutation
for i in range(500):
    source = f"""
[
    int(0)~val{i}
    <now>({random.randint(1, 100)})>val{i}
    <printf>^("Now mutated: {{val{i}}}\\n")
]
"""
    tests.append((f"now_mut_{i}", source))

# Category 20: Scope tests
for i in range(500):
    source = f"""
func{i}() [
    int(42)~local{i}
    <return>(local{i})
]
[
    int(~func{i}())~result{i}
    <printf>^("Scope result: {{result{i}}}\\n")
]
"""
    tests.append((f"scope_{i}", source))

print(f"Generated {len(tests)} test cases")

# Run all tests
start_time = time.time()
for idx, (name, source) in enumerate(tests):
    if idx % 1000 == 0:
        elapsed = time.time() - start_time
        print(f"Progress: {idx}/{len(tests)} ({elapsed:.1f}s) - Passed: {test_results['passed']}, Failed: {test_results['failed']}, Errors: {test_results['errors']}")
    make_test(name, source)

elapsed = time.time() - start_time
print(f"\n{'='*60}")
print(f"Test Results: {test_results}")
print(f"Total time: {elapsed:.2f}s")
print(f"Tests per second: {len(tests)/elapsed:.1f}")

if failures:
    print(f"\nFailures ({len(failures)}):")
    for name, error in failures[:50]:
        print(f"  {name}: {error[:200]}")
    if len(failures) > 50:
        print(f"  ... and {len(failures) - 50} more")