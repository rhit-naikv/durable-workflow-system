---
trigger: always_on
---

## Context7 MCP Usage

**Proactively use Context7 MCP** (via `resolve-library-id` and `query-docs` tools) without explicit requests when:

1. **Answering library/API questions** about project dependencies (Next.js, Supabase, Zod, React Testing Library, Tailwind, DaisyUI, Recharts, date-fns, TypeScript)
2. **Implementing features** requiring library setup, configuration, or integration patterns
3. **Generating code** that relies on external libraries (Server Actions with Supabase, Zod forms, Recharts charts, etc.)
4. **Determining best practices** for using a library in this project's context
5. **Debugging library-specific issues** (RLS errors, authentication flows, styling conflicts, deprecated APIs)

**Do NOT use Context7 for:**

- Project-specific patterns (use CLAUDE.md, PLANNING.md instead)
- Internal architecture questions (check codebase structure)
- Features fully documented in project files
- General software engineering (only library-specific guidance)
