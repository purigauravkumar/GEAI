# Security Policy

## Supported branch

Security fixes should be developed against the current default branch or an explicitly maintained security branch.

## Reporting a vulnerability

Please do not publish sensitive vulnerability details, credentials, private data, or working exploit material in a public issue.

For a private report, contact the repository owner through the GitHub account associated with this project and provide:

- affected file or endpoint
- vulnerability type
- security impact
- minimal reproduction steps
- suggested mitigation, if known

Allow reasonable time for investigation and remediation before public disclosure.

## Deployment warning

GEAI is an experimental personal AI project. The current API is designed primarily for local use and should not be exposed directly to an untrusted network. In particular, protect the API key, keep the service bound to localhost when possible, and review the crawler/network controls before accepting untrusted URLs.
