# Comprehensive Development Guide

## PART I: PYTHON CODING GUIDELINES

### Code Structure and Organization

1. Follow PEP 8 style guidelines for code formatting.
2. Limit line length to 79 characters for code and 72 for docstrings/comments.
3. Use 4 spaces for indentation (not tabs).
4. Organize imports in the following order:
   - Standard library imports
   - Related third-party imports
   - Local application/library specific imports
   - Separate import groups with a blank line
5. Use absolute imports rather than relative imports when possible.
6. Group related functionality into modules and packages.
7. Keep functions and methods short and focused on a single task.
8. Limit class inheritance depth to maintain code clarity.
9. Use composition over inheritance when appropriate.
10. Place module-level dunder names (like __all__, __version__) after imports but before other code.

### Naming Conventions

1. Use snake_case for functions, methods, and variables.
2. Use CamelCase for class names.
3. Use UPPER_CASE for constants.
4. Use ALL_CAPS_WITH_UNDERSCORES for module-level constants.
5. Use descriptive names that reveal intention.
6. Prefix private attributes with a single underscore (_private_attribute).
7. Use double underscore prefix for name mangling (__really_private).
8. Avoid single character variable names except for counters or iterators.
9. Prefix boolean variables with 'is_', 'has_', 'can_', etc. (is_valid, has_permissions).
10. Follow common Python idioms for special method names (__init__, __str__, etc.).

### Error Handling

1. Use specific exception types instead of catching generic Exception.
2. Use try/except blocks only around code that may actually raise an exception.
3. Keep try blocks as small as possible.
4. Use finally for cleanup code that must be executed regardless of exceptions.
5. Create custom exceptions for your application's error conditions.
6. Document exceptions raised by functions in docstrings.
7. Use context managers (with statement) to ensure proper resource cleanup.
8. Log exceptions with traceback information for debugging.
9. Return meaningful error messages that help identify the issue.
10. Avoid silencing exceptions without good reason.

### Performance Optimization

1. Profile code before optimizing to identify actual bottlenecks.
2. Use appropriate data structures for your use case (lists, sets, dictionaries).
3. Use list/dictionary/set comprehensions instead of loops when appropriate.
4. Use generators for large data sets to save memory.
5. Use built-in functions when possible (map, filter, any, all).
6. Be aware of string concatenation performance (use join() for many strings).
7. Minimize I/O operations by batching reads/writes.
8. Use lazy evaluation where appropriate.
9. Consider using NumPy or Pandas for numerical operations on large data sets.
10. Use asyncio for I/O-bound tasks and concurrent.futures for CPU-bound tasks.

### Documentation and Comments

1. Write docstrings for all public modules, functions, classes, and methods.
2. Follow Google or NumPy docstring format for consistency.
3. Include parameter types and return types in docstrings.
4. Document raised exceptions in docstrings.
5. Use comments to explain "why" not "what" the code is doing.
6. Keep comments up-to-date with code changes.
7. Use TODO, FIXME, and NOTE comments for temporary or pending work.
8. Document complex algorithms or non-obvious functionality.
9. Include examples in docstrings for complex functions.
10. Generate API documentation using tools like Sphinx.

### Testing

1. Write unit tests for all functionality using pytest or unittest.
2. Aim for high test coverage (>80% at minimum).
3. Use fixtures and parametrized tests to reduce test code duplication.
4. Mock external dependencies in tests.
5. Write both positive and negative test cases.
6. Include integration tests for workflows across multiple components.
7. Use test-driven development (TDD) when appropriate.
8. Run tests automatically in CI/CD pipelines.
9. Use property-based testing for functions with well-defined properties.
10. Test edge cases and boundary conditions explicitly.

### Security Best Practices

1. Never store secrets (passwords, API keys) in code.
2. Validate all user inputs before processing.
3. Use parameterized queries to prevent SQL injection.
4. Apply proper input sanitization when handling file paths.
5. Use secure random number generation for security-related functionality.
6. Implement proper access controls and authentication.
7. Keep dependencies updated to avoid known vulnerabilities.
8. Avoid using eval() or exec() with untrusted inputs.
9. Be careful with deserialization of untrusted data.
10. Log security-relevant events but avoid logging sensitive information.

### Version Control

1. Write clear and descriptive commit messages.
2. Keep commits small and focused on a single change.
3. Use feature branches for new development.
4. Run tests before committing changes.
5. Include relevant issue numbers in commit messages.
6. Use semantic versioning for releases.
7. Keep .gitignore updated to avoid committing temporary files.
8. Document breaking changes in release notes.
9. Review code before merging to main branches.
10. Ensure CI/CD pipelines pass before merging.

### Package Management

1. Use virtual environments for all Python projects.
2. Specify explicit dependency versions in requirements.txt or setup.py.
3. Consider using pip-tools or Poetry for dependency management.
4. Include all requirements, including development dependencies.
5. Pin dependencies to specific versions for reproducible builds.
6. Regularly update dependencies to get security fixes.
7. Use dependency scanning tools to identify vulnerabilities.
8. Document installation and setup procedures.
9. Consider containerization for consistent development environments.
10. Include license information for all dependencies.

### Code Quality and Maintenance

1. Use static type checking with mypy when possible.
2. Apply linters like flake8, pylint, or black for consistent code style.
3. Run static analysis tools as part of your development process.
4. Refactor code regularly to improve clarity and maintainability.
5. Eliminate code duplication through abstraction.
6. Keep functions and methods small (preferably under 50 lines).
7. Use meaningful variable names that explain their purpose.
8. Remove dead or unused code.
9. Keep cyclomatic complexity low (aim for < 10).
10. Use automated tools to enforce code quality standards.

## PART II: SYSTEMD SERVICE FILES GUIDE

### Common Patterns

#### Service File Structure
* Service files are typically stored in `/etc/systemd/system/` or `/usr/lib/systemd/system/`
* Files use the `.service` extension (e.g., `application.service`)
* Service files follow the INI file format with sections marked by `[Section]`
* Three main sections are commonly used: `[Unit]`, `[Service]`, and `[Install]`

#### [Unit] Section Patterns
* Contains metadata and dependency information
* Frequently includes `Description=` to describe the service's purpose
* Often defines relationships with other services using `After=`, `Requires=`, or `Wants=`
* May specify `Documentation=` to link to help resources

#### [Service] Section Patterns
* Defines the core service behavior
* Always includes `ExecStart=` to specify the command to start the service
* Commonly sets `Type=` to define the startup behavior (often `simple` or `forking`)
* Often specifies a user with `User=` to avoid running as root
* Frequently includes restart behavior with `Restart=` and `RestartSec=`
* May include resource controls like `LimitNOFILE=` or `MemoryLimit=`

#### [Install] Section Patterns
* Defines when the service should be started during boot
* Almost always includes `WantedBy=multi-user.target` for standard system services
* May include `Alias=` to create alternative names for the service

#### Common Service Types
* **Simple services**: Long-running processes with `Type=simple`
* **Forking services**: Daemons that fork with `Type=forking`
* **Oneshot services**: Quick tasks with `Type=oneshot` and `RemainAfterExit=yes`
* **Notify services**: Services that signal when they're ready with `Type=notify`

### Best Practices

#### Naming and Organization
1. Use descriptive, lowercase names for service files
2. Include the application name in the service name
3. Use consistent naming patterns across related services
4. Create a separate service file for each distinct application
5. Use drop-in configuration with `.d` directories for customizations

#### Security Practices
1. Avoid running services as root; use `User=` and `Group=`
2. Apply the principle of least privilege with appropriate permissions
3. Use `ProtectSystem=` and `ProtectHome=` to restrict filesystem access
4. Implement `PrivateTmp=yes` to isolate temporary files
5. Consider `NoNewPrivileges=true` to prevent privilege escalation
6. Use `CapabilityBoundingSet=` to limit capabilities

#### Reliability Practices
1. Configure appropriate restart behavior with `Restart=on-failure`
2. Add `RestartSec=` to prevent restart loops
3. Use `StartLimitIntervalSec=` and `StartLimitBurst=` to limit restart attempts
4. Implement proper dependencies with `After=` and `Requires=`
5. Use failure handling with `OnFailure=` for critical services

#### Performance and Resource Control
1. Set resource limits with `LimitCPU=`, `MemoryLimit=`, etc.
2. Use `CPUWeight=`, `IOWeight=` for resource prioritization
3. Implement `Nice=` to set process priority
4. Consider `OOMScoreAdjust=` to control out-of-memory behavior
5. Use `TimeoutStartSec=` and `TimeoutStopSec=` for appropriate timeouts

#### Documentation
1. Include a detailed `Description=` for each service
2. Add `Documentation=` links to relevant resources
3. Add comments above each section or option to explain purpose
4. Document dependencies and startup order
5. Include version information in comments

### Systemd Service Template

```ini
[Unit]
# Description of what the service does
Description=My Application Service

# Dependencies - services that should be started before this one
After=network.target
After=syslog.target

# Optional: For services that absolutely require another service
# Requires=another.service

# Optional: For services that should start if another service starts
# Wants=optional.service

# Optional: Documentation links
# Documentation=https://example.com/docs
# Documentation=man:myapp(1)

[Service]
# The type of service (simple: process remains in foreground)
Type=simple

# The command to start the service
ExecStart=/usr/bin/myapp --option1 --option2

# Optional: Commands to run before and after the main command
# ExecStartPre=/usr/bin/myapp-pre
# ExecStartPost=/usr/bin/myapp-post

# Optional: Command to stop the service (if special stop procedure needed)
# ExecStop=/usr/bin/myapp-stop

# Optional: Run as a specific user and group (instead of root)
User=appuser
Group=appgroup

# Restart policy (always, on-failure, on-abnormal, on-abort, on-watchdog)
Restart=on-failure
RestartSec=5s

# Limit restart attempts
StartLimitIntervalSec=500
StartLimitBurst=5

# Environment variables
Environment=NODE_ENV=production
# or read from a file
# EnvironmentFile=/etc/myapp/env

# Working directory
WorkingDirectory=/var/lib/myapp

# Security hardening
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true

# Resource limits
LimitNOFILE=65535
# MemoryLimit=512M
# CPUQuota=50%

[Install]
# Enable the service to start at boot
WantedBy=multi-user.target

# Optional: Create aliases for this service
# Alias=myapp.service
```

### Systemd Tips

#### Troubleshooting
1. Use `systemctl status service-name` to check service status and recent logs
2. View detailed logs with `journalctl -u service-name`
3. Follow logs in real-time with `journalctl -fu service-name`
4. Debug startup issues with `systemctl start --no-block service-name`
5. Verify configuration with `systemd-analyze verify service-name.service`
6. Check dependency issues with `systemctl list-dependencies service-name`

#### Common Errors and Solutions
1. **Failed to start**: Check ExecStart path and permissions
2. **Exit code 1**: Application error; check application logs
3. **Dependency failures**: Verify required services with list-dependencies
4. **Permission denied**: Check User/Group settings and file permissions
5. **Resource limits**: Adjust resource controls or system limits

#### Optimization
1. Use socket activation for on-demand services
2. Implement service sandboxing for security
3. Set appropriate CPU and I/O priorities for important services
4. Use condition directives to control when services start
5. Implement cgroup controls for precise resource management

#### Advanced Features
1. Use `ExecStartPre=` and `ExecStartPost=` for setup and cleanup
2. Implement service watchdogs for automatic monitoring
3. Use `systemd-notify` with Type=notify for precise startup control
4. Create template units with `@` for multiple service instances
5. Leverage systemd timers instead of cron jobs

#### Management Commands
1. Enable at boot: `systemctl enable service-name`
2. Start immediately: `systemctl start service-name`
3. Reload configuration: `systemctl daemon-reload`
4. Restart service: `systemctl restart service-name`
5. Check logs: `journalctl -u service-name`
6. Check status: `systemctl status service-name`

## PART III: CREATING PYTHON SYSTEMD SERVICES

### Python Application as a Systemd Service

When deploying Python applications as systemd services, combine the best practices from both sections:

1. Use virtual environments with absolute paths in your service file
2. Include proper error handling in your Python application
3. Implement logging that works well with journald
4. Consider appropriate resource limits for Python processes
5. Use environment files to separate configuration from code

### Example Python Service

```ini
[Unit]
Description=Python Application Service
After=network.target

[Service]
Type=simple
User=pythonapp
Group=pythonapp
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/venv/bin/python /opt/myapp/main.py
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

# Resource limits for memory-hungry Python apps
LimitNOFILE=65535
MemoryLimit=512M

# Security hardening
PrivateTmp=true
ProtectSystem=full
ProtectHome=read-only
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

### Python Systemd Integration Best Practices

1. Use `PYTHONUNBUFFERED=1` to prevent output buffering
2. Include proper signal handling in your Python code
3. Implement graceful shutdown to respond to systemd stop commands
4. Use a dedicated user for the Python service
5. Leverage systemd for monitoring and automatic restarts
6. Implement proper logging with structured log formats
7. Use environment files for configuration
8. Ensure Python dependencies are properly installed in the virtualenv
9. Consider using Python's daemon libraries for complex services
10. Implement health check endpoints for monitoring



@/home/claudebypass/projects/code_snippets/CONTEXT.md
@/home/claudebypass/projects/code_snippets/DB_README.md