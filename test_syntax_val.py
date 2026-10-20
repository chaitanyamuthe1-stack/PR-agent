import ast

def validate_code_syntax(code: str, language: str):
    if not code or not code.strip():
        return False, "Code is empty"
    lang = language.lower().strip()
    if lang in ["python", "py"]:
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Python SyntaxError on line {e.lineno}: {e.msg}"
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    escaped = False
    i = 0
    n = len(code)
    line_num = 1
    while i < n:
        char = code[i]
        if char == '\n':
            line_num += 1
            in_line_comment = False
            escaped = False
            i += 1
            continue
        if in_line_comment:
            i += 1
            continue
        if in_block_comment:
            if char == '*' and i + 1 < n and code[i + 1] == '/':
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if escaped:
            escaped = False
            i += 1
            continue
        if char == '\\':
            escaped = True
            i += 1
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            i += 1
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            i += 1
            continue
        if in_double_quote or in_single_quote:
            i += 1
            continue
        if char == '/' and i + 1 < n:
            if code[i + 1] == '/':
                in_line_comment = True
                i += 2
                continue
            elif code[i + 1] == '*':
                in_block_comment = True
                i += 2
                continue
        if char == '#' and lang in ["ruby", "rb", "python", "py"]:
            in_line_comment = True
            i += 1
            continue
        if char in '({[':
            stack.append((char, line_num))
        elif char in ')}]':
            if not stack:
                return False, f"Unexpected closing '{char}' on line {line_num}"
            top, top_line = stack.pop()
            if top != pairs[char]:
                return False, f"Mismatched delimiter: expected closing for '{top}' (line {top_line}) but found '{char}' on line {line_num}"
        i += 1
    if stack:
        unclosed, u_line = stack[-1]
        return False, f"Unclosed delimiter '{unclosed}' from line {u_line}"
    return True, None

# Test valid python
assert validate_code_syntax("def foo():\n    return 1", "python") == (True, None)
# Test invalid python
res, err = validate_code_syntax("def foo(:\n    return 1", "python")
assert not res
print("Python invalid test passed:", err)

# Test valid C++
assert validate_code_syntax('#include <iostream>\nint main() { std::cout << "{"; return 0; }', "cpp") == (True, None)
# Test invalid C++ (unclosed brace)
res, err = validate_code_syntax("#include <iostream>\nint main() { return 0;", "cpp")
assert not res
print("C++ invalid test passed:", err)

# Test valid Java
assert validate_code_syntax("public class Main { public static void main(String[] args) {} }", "java") == (True, None)
# Test valid JS
assert validate_code_syntax("function hello() { return [1, 2, 3]; }", "javascript") == (True, None)
# Test valid Ruby
assert validate_code_syntax("def foo\n  puts 'hello'\nend", "ruby") == (True, None)

print("ALL SYNTAX VALIDATION CHECKS PASSED!")
