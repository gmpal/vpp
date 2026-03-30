# Logical Test Questionnaire

Use this checklist to validate whether adding/editing/removing buildings produces sensible production and consumption behavior.

1. With no households and no sources, is total production exactly 0?
2. With no households and no EVs, is total consumption exactly 0 (or near-zero if baseline load is expected by design)?
3. After adding one household with solar panels, does production become > 0 within the expected refresh window?
4. If we add a household with 0 solar panels, does production stay unchanged while consumption increases?
5. If we increase one household's panel count by +1, does production increase (all else equal)?
6. If we decrease panel count by -1, does production decrease and never go negative?
7. After adding a second similar household, does total production increase approximately additively?
8. After adding a second similar household, does total consumption increase approximately additively?
9. If num_people increases for one household, does that household's consumption contribution increase?
10. Is per-household consumption in a realistic range (no negative values, no impossible spikes, no flatline artifacts)?
11. Does net power (production - consumption) move in the expected direction when adding more panels?
12. During low-sun periods (night), does production fall toward 0 while consumption stays positive?
13. During daytime, does production rise compared to nighttime for the same setup?
14. After deleting a household, do both production and consumption decrease accordingly?
15. After deleting a household with EVs, are EV-related effects removed from totals?
16. If a household is created and then edited quickly, do metrics converge to one consistent final state (no double counting)?
17. After repeated add/remove of the same household, do totals return to baseline without drift?
18. Are dashboard totals consistent with map/popup values for the same household?
19. Is update latency acceptable (for example, visible within one polling cycle)?
20. Do all values remain physically valid over time: production >= 0, consumption >= 0, SOC in bounds, no NaN/null chart points?
