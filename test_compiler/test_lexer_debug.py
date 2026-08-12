import sys
sys.path.insert(0, '/workspaces/compiler-ko-')
from ko_compiler import KoLexer

for source in ['a', 'int', 'int(10)', 'int(10)~hp']:
    print(f"Tokenizing: {source!r}", flush=True)
    lexer = KoLexer(source)
    tokens = lexer.tokenize()
    print(f"  Got {len(tokens)} tokens", flush=True)
print("All done", flush=True)
