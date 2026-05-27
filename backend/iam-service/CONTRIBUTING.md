# Contributing to HamDong IAM Service

## Code Quality Standards

### Architecture
- Follow **Clean Architecture** with strict layer separation
- Never place business logic in controllers
- Keep domain layer free from framework imports
- Use repositories for data access abstraction

### Coding Standards
- Use type hints for all functions
- Maximum function length: 50 lines
- Maximum class length: 200 lines
- Follow SOLID principles
- Write self-documenting code with clear naming

### SOLID Principles Checklist
- [ ] **S**ingle Responsibility: Does the class have one reason to change?
- [ ] **O**pen/Closed: Is it open for extension but closed for modification?
- [ ] **L**iskov Substitution: Do all implementations satisfy the interface contract?
- [ ] **I**nterface Segregation: Are interfaces focused and minimal?
- [ ] **D**ependency Inversion: Do you depend on abstractions, not concrete types?

## Before Committing

1. **Write Tests**
   - Unit tests for use cases
   - Integration tests for repositories
   - API tests for endpoints
   - Minimum 80% coverage

2. **Format Code**
   ```bash
   black src/ tests/
   ```

3. **Run Linter**
   ```bash
   pylint src/
   ```

4. **Run All Tests**
   ```bash
   pytest --cov=src
   ```

5. **Update Documentation**
   - Document public APIs
   - Update README if needed
   - Add docstrings to new functions

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **test**: Test additions
- **refactor**: Code refactoring
- **style**: Code style changes
- **perf**: Performance improvements

### Example
```
feat(auth): implement OTP request endpoint

- Add RequestOTPUseCase for OTP logic
- Implement RedisOTPRepository for storage
- Add rate limiting per phone and IP
- Include comprehensive test coverage

Closes #123
```

## Layer Guidelines

### Domain Layer (`src/domain/`)
✅ DO:
- Define entities and interfaces
- Create domain exceptions
- Use plain Python classes
- Document business rules

❌ DON'T:
- Import external libraries (except typing)
- Access database or cache
- Use FastAPI or framework code

### Application Layer (`src/application/`)
✅ DO:
- Implement use cases
- Define DTOs
- Orchestrate business logic
- Use interfaces from domain

❌ DON'T:
- Access HTTP or database directly
- Mix multiple domains in one use case
- Create framework-specific code

### Infrastructure Layer (`src/infrastructure/`)
✅ DO:
- Implement interfaces
- Handle external integrations
- Manage data persistence
- Implement security operations

❌ DON'T:
- Place business logic here
- Expose implementation details
- Violate abstraction boundaries

### Presentation Layer (`src/presentation/`)
✅ DO:
- Keep controllers thin
- Validate HTTP requests
- Handle HTTP errors
- Call use cases

❌ DON'T:
- Implement business logic
- Access database directly
- Mix multiple concerns

## Testing Best Practices

### Unit Tests
- Test one thing per test
- Use meaningful test names
- Mock external dependencies
- Test both success and failure cases

### Integration Tests
- Test component interaction
- Use real or in-memory databases
- Test error scenarios
- Verify side effects

### API Tests
- Test all happy paths
- Test error responses
- Verify status codes
- Test request validation

### Test Structure
```python
def test_something():
    # Arrange - Set up test data
    data = create_test_data()
    
    # Act - Execute the code
    result = function_under_test(data)
    
    # Assert - Verify results
    assert result == expected_value
```

## Pull Request Process

1. Create feature branch: `git checkout -b feat/feature-name`
2. Implement feature following guidelines
3. Write comprehensive tests
4. Update documentation
5. Format code: `make format`
6. Run tests: `make test-coverage`
7. Push and create pull request
8. Ensure CI passes
9. Request review from maintainers

## Code Review Checklist

- [ ] Follows Clean Architecture
- [ ] Has adequate test coverage
- [ ] Follows SOLID principles
- [ ] Code is well-documented
- [ ] No hardcoded values
- [ ] Error handling is complete
- [ ] Performance is acceptable
- [ ] Security concerns addressed

## Reporting Issues

Please include:
- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Python version, etc.)
- Error logs/stack traces

## Questions?

Open an issue or reach out to the maintainers.
