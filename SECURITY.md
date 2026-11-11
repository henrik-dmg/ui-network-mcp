# Security policy

## Supported versions

Only the latest release gets security fixes.

## Report a vulnerability

Do not open a public issue for a security problem. Report the problem privately:

1. Open the **Security** tab of the repository.
2. Click **Report a vulnerability**.
3. Write the version of the server, the steps that show the problem, and the effect of the problem.

The maintainer replies to each report, and publishes a fix and an advisory when the problem is confirmed.

## Scope

These are examples of security problems in this project:

- A tool result shows a secret, for example a WiFi passphrase.
- The server shows a write tool when `UNIFI_ALLOW_WRITES` is not `true`.
- The server sends the API key to a host that is not the configured console or the UniFi cloud connector.
- The server accepts an incorrect TLS certificate when `UNIFI_VERIFY_TLS` is `true`.

These problems are not in the scope of this policy:

- A problem in the UniFi Network API or in the UniFi console. Report it to Ubiquiti.
- A change that an agent makes with a write tool after a person approved the tool call.
