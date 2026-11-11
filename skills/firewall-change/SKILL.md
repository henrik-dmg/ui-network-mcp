---
name: firewall-change
description: Safe change of the UniFi firewall, to create, change, delete, or reorder a firewall policy, with a plan and the approval of the user before each write. Use when the user asks to block or allow traffic on a UniFi network, or to fix a finding of a firewall audit.
---

# UniFi firewall change

Change the firewall in four phases: **intent**, **plan**, **apply**, and **check**. Write nothing before the user approves the plan.

Caution: A wrong policy can block the access to the console, and also the access of this server. Before you block traffic to the `Gateway` zone, or between the zone of the user and other zones, make sure that the user keeps a way to reach the console, for example the UniFi app through unifi.ui.com.

## Steps

1. Make sure that the write tools are available, for example `create_firewall_policy`. If they are not available, tell the user to turn on the plugin option "Allow changes", and to use an API key with write access. Then stop.
2. **Intent.** Write the change as these parts: the action (ALLOW, BLOCK, or REJECT), the source zone and source filter, the destination zone and destination filter, the protocols and ports, the schedule, and the position in the order. Ask the user about each part that is not clear. The direction of the traffic is frequently not clear: "block the cameras from the internet" can mean either direction.
3. **Current state.** Call `get_firewall_overview`, and `get_firewall_policy_ordering` for the zone pair. Get the IDs for the filters from `list_networks`, `list_traffic_matching_lists`, `list_vpn_servers`, `list_dpi_applications`, or `list_dpi_categories`.
4. **Conflicts.** In the zone pair, find:
   - A policy that already does the change. Then no change is necessary. Tell the user.
   - An earlier enabled policy that matches the same traffic. The new policy would never apply, so the plan must also reorder the policies.
   - A later policy that the new policy would shadow. Tell the user.
5. **Plan.** Show the plan to the user:
   - Each write, in plain words and with the tool arguments.
   - The order of the zone pair after the change.
   - The risks, from the caution above.
   - How to undo the change.

   Get the approval of the user for the plan. Any change to the plan needs a new approval.
6. **Apply.** Make the writes of the plan, in the order of the plan:
   - `create_firewall_policy` puts a new policy before the system-defined policies of the zone pair.
   - To move a policy, call `get_firewall_policy_ordering` again, then call `reorder_firewall_policies` with all policy IDs of the zone pair in the new order.
   - `update_firewall_policy` replaces each given field completely. The console does not let you change a system-defined policy, except `logging_enabled` and `report_flow_enabled`.
   - Before you call `delete_firewall_policy`, call `get_firewall_policy`, and make sure that the policy is the policy of the plan.

   If a write fails, stop, and show the error to the user. Make no other writes that the plan did not include.
7. **Check.** Call `get_firewall_overview` again. Make sure that each policy of the plan is in the correct zone pair, at the correct position, with the correct `enabled` state.

The change is complete when the check of step 7 agrees with the plan.

## Report

1. The policies that changed, with their IDs.
2. The order of the zone pair after the change.
3. How to undo the change: `delete_firewall_policy` for a new policy, or `update_firewall_policy` with the old values for a changed policy. A deleted policy cannot be restored, only created again.
