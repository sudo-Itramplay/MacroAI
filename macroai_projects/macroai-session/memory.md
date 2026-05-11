[PROJECT_STATE]
- Active: src/{agents.py,graph.py,main.py,__init__.py} | Existing LangGraph scaffold
- Arch: Flat src/, no models/pkg yet
- Broken: None

[TASK_STACK]
- Done: Req analysis; complexity classification (simple)
- In-Progress: None
- Pending[OPENCODE]: Implement User base class at src/user.py w/ locked attrs (id, username, email, password_hash, is_active, created_at), explicit TypeHints, email regex + non-empty str validation
- Pending[CLAUDE]: None

[KEY_DECISIONS]
- Attrs locked: id, username, email, password_hash, is_active, created_at | Rationale: Req spec | Owner: OPENCODE
- Explicit typing mandatory | Rationale: Req spec | Owner: OPENCODE
- Basic format validation mandatory (email regex, non-empty strings) | Rationale: Req spec | Owner: OPENCODE

[SCRATCHPAD]
- Greenfield; no debug cycles
- Implementation choice: stdlib @dataclass or Pydantic v2 (check requirements.txt before import)

[NEXT_ACTION]
- Target: OPENCODE
- Task: Implement User class in new src/user.py module using chosen model lib; add all locked attrs w/ types; include email regex + non-empty str validation
- Files: src/user.py
- Signature: class User