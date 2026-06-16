# What is a Lint Error?

## Definition

A **lint error** is a warning or error flagged by a **linter** — a static analysis tool that reads your source code *without running it* and reports potential problems.

The name comes from the Unix `lint` tool (1978), which picked "fluff" out of C code like a lint roller picks fluff off clothes.

---

## What a Linter Checks

| Category | Example |
|---|---|
| **Syntax errors** | Missing semicolon, unclosed bracket |
| **Undefined variables** | Using `foo` before declaring it |
| **Unused variables** | `const x = 5;` that is never read |
| **Type mismatches** | Passing a string where a number is expected |
| **Style violations** | Wrong indentation, line too long |
| **Bad patterns** | Using `==` instead of `===` in JavaScript |
| **Security issues** | `eval()`, `dangerouslySetInnerHTML` without reason |

---

## Lint vs. Runtime Error

| | Lint Error | Runtime Error |
|---|---|---|
| **When found** | Before code runs (static analysis) | While code is executing |
| **Needs execution?** | No | Yes |
| **Example** | Variable declared but never used | `null.property` crash |

---

## Common Linters by Language

| Language | Linter |
|---|---|
| JavaScript / TypeScript | ESLint |
| Python | Ruff, Flake8, Pylint |
| CSS | Stylelint |
| Go | golangci-lint |
| Rust | Clippy |

---

## Example — ESLint (JavaScript)

```js
// This code has two lint errors:
const name = "Alice"   // Error 1: missing semicolon (if enforced)
console.log(age)       // Error 2: 'age' is not defined
```

ESLint output:
```
1:20  warning  Missing semicolon                semi
2:13  error    'age' is not defined             no-undef
```

Each line shows: `line:column  severity  message  rule-name`

---

## Example — Python (Ruff / Flake8)

```python
import os          # F401: 'os' imported but unused
x=1+2              # E225: missing whitespace around operator
```

---

## Severity Levels

- **Error** — must be fixed; often blocks CI/CD pipelines or builds
- **Warning** — should be fixed; doesn't block but indicates bad practice
- **Info / Hint** — stylistic suggestion

---

## Why Lint Errors Matter

1. **Catch bugs early** — before they reach production
2. **Enforce consistency** — same style across the whole team
3. **Improve readability** — code is easier to review and maintain
4. **Block bad merges** — CI pipelines fail on lint errors, protecting the main branch

---

## How to Fix Them

1. Read the rule name (e.g., `no-undef`, `E501`)
2. Look up what the rule means
3. Fix the code — or, if intentional, suppress with a comment:
   ```js
   // eslint-disable-next-line no-console
   console.log("debug")
   ```
   Use suppressions sparingly — they hide real problems.

---

## In This Project

- **Frontend:** ESLint via Vite's default config — run `npm run lint` inside `frontend/`
- **Backend:** Python linting can be run with `ruff check .` or `flake8` inside `backend/`
