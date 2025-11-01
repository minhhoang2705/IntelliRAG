## TDD Fundamentals

### When Multiple Tests Are Allowed
You can write multiple test in on Red phase when they meet these criteria:

1. **Same Behavioral Unit**: Tests cover the same method/function/feature
   - ✅ Testing `add(a, b)` with different inputs: `(1, 2)`, `(0, 0)`, `(-1, 5)`
   - ✅ Testing edge case: empty string, null, boundary values
   - ❌ Testing multiple unrelated methods: `add()`, `subtract()`, `multiply()`

2. **Similar Complexity**: All tests require roughly the same implementation effort
   - ✅ Three validation tests for email format
   - ✅ Multiple CRUD operations of similar complexity
   - ❌ Mix of simple getter and complex algorithms

3. **Clear Dependency Order**: Tests naturally group together without interdependencies
   - ✅ Constructor parameter validation (all parameters at once)
   - ✅ Symmetric operations (upload/download, encode/decode)
   - ❌ Tests that build on each other's state

### The TDD Cycle
The foundation of TDD is the Red-Green-Refactor cycle:

1. Red Phase (Batch): Write 2-5 related failing tests
   - Group must be cohesive (same feature/behavior)
   - All tests must fail for the RIGHT reason
   - Maximum 5 tests per batch (to avoid over-implementation)
   - Document why these tests are batched together

2. Green Phase (Minimal): Write code to pass ALL batched tests
   - Implementation should be straightforward for the entire batch
   - If implementation becomes complex, batch was too large → split it
   - No anticipatory code beyond the test batch

3. Refactor Phase: Same rules apply
   - All tests in batch must be green
   - Improve structure of implementation AND tests

### Quality Safeguards
To maintain quality with batched tests:

1. **Batch Size Limits**
Maximum batch sizes:
   - Simple functions (getters, setters): 5 tests
   - Business logic (validation, calculation): 3 tests
   - Complex algorithms: 2 tests
   - Integration tests: 1 test (traditional TDD)

2. **Must Document Batch Rationale**

When adding multiple tests, state:

   "Batching these 3 tests because they all test input validation
   for the same method with different invalid inputs (null, empty,
   invalid format). Implementation will be a single validation
   function."

3. **Stop and Split If:**
   -  Implementation becomes unclear or complex
   -  Tests take >10 minutes to make pass
   -  You're adding untested code paths
   -  Tests are failing for different reasons


4. **Verification Checkpoint**

   Before implementing, verify:
      - [ ] All tests fail (run them!)
      - [ ] Failure messages are correct and expected
      - [ ] Tests are independent (can run in any order)
      - [ ] Implementation approach is clear for ALL tests

### Core Violations

1. **Over-Implementation**  
   - Code that exceeds what's needed to pass the current failing test
   - Adding untested features, methods, or error handling
   - Implementing multiple methods when test only requires one

2. **Premature Implementation**
   - Adding implementation before a test exists and fails properly
   - Adding implementation without running the test first
   - Refactoring when tests haven't been run or are failing

### Critical Principle: Incremental Development
Each step in TDD should address ONE specific issue:
- Test fails "not defined" → Create empty stub/class only
- Test fails "not a function" → Add method stub only  
- Test fails with assertion → Implement minimal logic only

### General Information
- Sometimes the test output shows as no tests have been run when a new test is failing due to a missing import or constructor. In such cases, allow the agent to create simple stubs. Ask them if they forgot to create a stub if they are stuck.
- It is never allowed to introduce new logic without evidence of relevant failing tests. However, stubs and simple implementation to make imports and test infrastructure work is fine.
- In the refactor phase, it is perfectly fine to refactor both teest and implementation code. That said, completely new functionality is not allowed. Types, clean up, abstractions, and helpers are allowed as long as they do not introduce new behavior.
- Adding types, interfaces, or a constant in order to replace magic values is perfectly fine during refactoring.
- Provide the agent with helpful directions so that they do not get stuck when blocking them.
