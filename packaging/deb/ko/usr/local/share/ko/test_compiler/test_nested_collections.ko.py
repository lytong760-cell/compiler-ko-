import sys
sys.path.insert(0, '.')
from ko_compiler import KoLexer, KoParser, KoInterpreter, KoCompileError

def test_case(name, source, expect_error=False):
    try:
        lexer = KoLexer(source)
        tokens = lexer.tokenize()
        parser = KoParser(tokens)
        program = parser.parse()
        interpreter = KoInterpreter(program)
        interpreter.run()
        if expect_error:
            print(f"FAIL {name}: expected error but succeeded")
            return False
        print(f"PASS {name}")
        return True
    except Exception as e:
        if expect_error:
            print(f"PASS {name}: got expected error: {e}")
            return True
        print(f"FAIL {name}: {e}")
        return False

tests = [
    ("nested_dict_index", '''
[
    {'a': {'b': 42}}~data
    int(data{'a'}{'b'})~val
    <printf>^("val={val}\\n")
]
'''),
    ("nested_list_index", '''
[
    (1, (2, 3))~nested
    int(nested<1><0>)~val
    <printf>^("val={val}\\n")
]
'''),
    ("mixed_index", '''
[
    {'items': (10, 20, 30)}~data
    int(data{'items'}<1>)~val
    <printf>^("val={val}\\n")
]
'''),
    ("missing_key", '''
[
    {'a': 1}~dic
    <catch>(`KeyNotFoundError`) [
        <printf>^("caught missing key\\n")
    ]
    dic{'nonexistent'}
]
'''),
    ("bare_id_dict_key", '''
[
    (1{'a'}, 2{'b'})~dic
    <printf>^("dic{'a'}={dic{'a'}}, dic{'b'}={dic{'b'}}\\n")
]
'''),
]

passed = 0
failed = 0
for item in tests:
    name = item[0]
    source = item[1]
    expect_error = item[2] if len(item) > 2 else False
    if test_case(name, source, expect_error):
        passed += 1
    else:
        failed += 1

print(f"\n{passed} passed, {failed} failed")
