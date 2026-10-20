# PR Agent — Static Analysis & Tool Installation Guide

This document describes the native static analysis tools, linters, and compiler-based syntax verification checks supported by the PR Agent Multi-Agent Engine.

---

## 1. Engine Philosophy & Safety Invariants

1. **Zero Silent Installations**: The engine NEVER attempts to run `pip install`, `npm install -g`, `choco`, `brew`, or `apt-get` silently in the background. It respects developer autonomy and system integrity.
2. **Transparent Tool Availability**: The engine accurately captures and reports whether a tool is natively installed in `PATH` or missing. It never claims an uninstalled tool ran.
3. **Partial Coverage Transparency**: When a tool is not installed, the engine continues operating under partial coverage using deterministic AST and pattern inspection rules, clearly noting the tool's absence and providing installation instructions.
4. **Zero Untrusted Execution**: Safe compiler syntax checks (`gcc -fsyntax-only`, `node --check`, `ruby -c`, `ast.parse`) strictly inspect and validate syntax without linking, generating binaries, or executing untrusted code.

---

## 2. Language-Specific Tooling Matrix

| Language | Primary Tools | Role | Optional Compiler / Syntax Check |
| :--- | :--- | :--- | :--- |
| **Python** | `bandit`, `pylint` | Security taint analysis & code quality | `compile(code, ..., 'exec')` / `ast.parse` |
| **C / C++** | `cppcheck` | Memory leak, buffer overrun, undefined behavior | `g++ -fsyntax-only` / `clang++ -fsyntax-only` |
| **Java** | `checkstyle` | Standards compliance & resource management | `javac -d <temp> -Xlint:all` (compile only) |
| **JavaScript** | `eslint` | ECMAScript runtime defects & secret detection | `node --check` (syntax verification only) |
| **Ruby** | `rubocop` | Ruby security, syntax, and style guidelines | `ruby -c` (syntax check only) |

---

## 3. Installation Instructions by Platform

### A. Python (Bandit & Pylint)
- **Pip (All Platforms)**:
  ```bash
  pip install bandit pylint
  ```
- **Verification**:
  ```bash
  bandit --version
  pylint --version
  ```

### B. C & C++ (Cppcheck & GCC/Clang)
- **Windows (Chocolatey / WinGet)**:
  ```powershell
  choco install cppcheck
  # Optional safe compiler:
  choco install mingw
  ```
  *or with WinGet:*
  ```powershell
  winget install Cppcheck.Cppcheck
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get update && sudo apt-get install -y cppcheck g++
  ```
- **macOS (Homebrew)**:
  ```bash
  brew install cppcheck gcc
  ```
- **Verification**:
  ```bash
  cppcheck --version
  g++ --version
  ```

### C. Java (Checkstyle & OpenJDK)
- **Windows (Chocolatey)**:
  ```powershell
  choco install openjdk checkstyle
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get install -y default-jdk checkstyle
  ```
- **macOS (Homebrew)**:
  ```bash
  brew install openjdk checkstyle
  ```
- **Verification**:
  ```bash
  checkstyle --version
  javac -version
  ```

### D. JavaScript (ESLint & Node.js)
- **All Platforms**:
  ```bash
  # Node.js provides the safe 'node --check' syntax verification:
  # Download from https://nodejs.org or via package manager:
  npm install -g eslint
  ```
- **Windows (Chocolatey / WinGet)**:
  ```powershell
  choco install nodejs
  npm install -g eslint
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get install -y nodejs npm
  sudo npm install -g eslint
  ```
- **macOS (Homebrew)**:
  ```bash
  brew install node
  npm install -g eslint
  ```
- **Verification**:
  ```bash
  node --version
  eslint --version
  ```

### E. Ruby (RuboCop & Ruby Interpreter)
- **Windows (Chocolatey)**:
  ```powershell
  choco install ruby
  gem install rubocop
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get install -y ruby ruby-dev
  sudo gem install rubocop
  ```
- **macOS (Homebrew)**:
  ```bash
  brew install ruby
  gem install rubocop
  ```
- **Verification**:
  ```bash
  ruby -v
  rubocop -v
  ```

---

## 4. Normalized Output Schema

All tools normalize findings into this standard schema:

```json
{
  "tool": "bandit",
  "rule_id": "Bandit:B608",
  "line": 15,
  "column": 1,
  "message": "Possible SQL injection vector through string-based query construction",
  "severity": "critical",
  "category": "security",
  "cwe": "CWE-89",
  "tool_available": true,
  "evidence_type": "native_static_linter"
}
```

Tool execution telemetry is captured per analysis run:

```json
{
  "tool": "bandit",
  "installed": true,
  "path": "C:\\Python312\\Scripts\\bandit.EXE",
  "status": "executed",
  "exit_code": 1,
  "execution_time_ms": 142.5,
  "findings_count": 2,
  "message": "Native bandit security scanner executed."
}
```
