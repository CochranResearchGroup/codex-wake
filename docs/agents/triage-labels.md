# Triage labels

Exactly one category and one state for each triaged issue. Resolve conflicting
states with the maintainer; preserve unrelated provider labels.

| Role | Provider label |
| --- | --- |
| bug | bug |
| enhancement | enhancement |
| needs-triage | needs-triage |
| needs-info | needs-info |
| ready-for-agent | ready-for-agent |
| ready-for-human | ready-for-human |
| wontfix | wontfix |

New categories/states or label taxonomy changes require separate operator
scope; missing mappings/provider labels fail closed. Setup admits the four
missing default states; existing bug, enhancement and wontfix are reused.
