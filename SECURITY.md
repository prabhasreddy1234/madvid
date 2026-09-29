# Security Policy

## Supported versions

The project currently supports the repository version in development and the latest released version.

## Reporting vulnerabilities

Please disclose vulnerabilities privately. Do not open a public issue for a security concern.

## Security practices

MADVID intentionally:

- redacts common secrets and tokens before logs or metadata
- ignores `.env` and credential files by default
- never executes Git commands
- never uploads project source unless explicitly configured by the user
- avoids fabricating functionality or data from a source that could not be verified
