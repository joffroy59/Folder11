# Not Allowed Operations

This document lists operations that are strictly forbidden within this project. Adherence to these rules is mandatory to maintain code quality, history integrity, and team collaboration.

## Git Operations
- **Force Push (git push --force or git push --force-with-lease):** Force pushing to shared branches is strictly prohibited. This action rewrites commit history and can lead to lost work and significant integration issues for other team members. Always use standard `git push` and resolve conflicts through merges or rebases (followed by a standard push).
