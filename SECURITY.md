# Security Policy

## Supported Versions

Cortex is currently in alpha. Security fixes will be applied to the latest
`main` branch and the latest alpha tag when feasible.

## Reporting a Vulnerability

Do not open public issues for suspected vulnerabilities.

Report security issues privately through GitHub Security Advisories:
`https://github.com/howaeri/cortex-loop/security/advisories/new`

Include:
- affected version/commit
- reproduction steps
- impact assessment
- any proposed mitigation

## Response Targets

- Acknowledgement: within 48 hours
- Initial triage: within 5 business days
- Mitigation plan or fix ETA: within 10 business days when reproducible

## Disclosure Process

- We will coordinate disclosure timing with reporters.
- Fixes may be released before full technical details are published.
- Once patched, a public advisory summary will be added to release notes.

## Security Boundaries and Risks

- `invariants.execution_mode = "host"` runs test code on the host machine.
  Use only for trusted repositories.
- For untrusted codebases, use `invariants.execution_mode = "container"` and
  review the container runtime boundary.
- In alpha, treat all hook payload content as untrusted input and prefer
  strict structured stop payload settings.
