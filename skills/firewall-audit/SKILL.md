---
name: firewall-audit
description: Audit of the firewall policies of a UniFi site, for shadowed, too broad, duplicate, and unused policies and objects. Use when the user asks to review, audit, check, or clean up the UniFi firewall, or asks if the firewall is secure.
---

# UniFi firewall audit

Examine each user-defined firewall policy of a UniFi site against the checks below, and report the **findings**. Each finding names the policy, the zone pair, the check, and the evidence. All tools in this skill are read-only.

## How the firewall works

- A policy belongs to one zone pair: a source zone and a destination zone. `get_firewall_overview` shows the policies of each zone pair in the order of evaluation (`index`).
- The console applies the first enabled policy that matches the traffic. A later policy does not apply to traffic that an earlier policy matched.
- `origin` tells who made a policy. `USER_DEFINED` policies are from the user. `SYSTEM_DEFINED` policies are the defaults of the console. `DERIVED` policies are the return traffic of an ALLOW policy with `allowReturnTraffic`. Audit only the `USER_DEFINED` policies, and use the other policies as context.
- A traffic filter with `matchOpposite` matches all values except the given values.
- A policy without a source filter or without a destination filter matches all traffic of that side of the zone pair.

## Steps

1. Call `get_firewall_overview`. If the tool asks for a `site_id`, call `list_sites`, and ask the user which site to audit.
2. Call `find_unused_objects`.
3. For each zone pair, examine each `USER_DEFINED` policy in order against each check in the table below.
4. Write the report.

The audit is complete when each user-defined policy of each zone pair was examined against each check. Count the policies, and give the count in the report.

## Checks

| Check | Finding | Severity |
|-|-|-|
| Shadowed | An earlier enabled policy in the same zone pair matches all the traffic of a later policy. The later policy never applies. If the two policies have different actions, the severity is high. | High or medium |
| Too broad | An ALLOW policy has no source filter and no destination filter, and matches all protocols. If the source zone is the internet (`External`), the severity is high. | High or medium |
| Open port from the internet | An ALLOW policy from the `External` zone to an internal zone allows a port. Name the port and the destination. | Medium |
| Duplicate | Two policies in the same zone pair have the same filters, the same protocol scope, and the same action. | Low |
| No logging | A BLOCK or REJECT policy has `loggingEnabled` false. Blocked traffic is then not visible in the logs. | Low |
| Disabled | A user-defined policy is disabled. It can be a remainder of an old change. | Low |
| Unused object | `find_unused_objects` shows a traffic matching list that no policy uses, or a custom zone without networks. | Low |

A schedule, a connection state filter, or an IPsec filter makes a policy match less traffic. Consider these filters before you report a policy as shadowed or too broad. If you are not sure that a policy is shadowed, report it as "possibly shadowed", and give the reason.

## Report

1. One sentence: the number of zone pairs and user-defined policies, and the number of findings by severity.
2. A table with the columns Severity, Check, Policy (name and ID), Zone pair, Evidence, and Suggested fix. Put the most severe finding first.
3. The zone pairs without findings, in one line.

To fix a finding, use the `firewall-change` skill. Each fix changes the network, so the user must approve it first.
