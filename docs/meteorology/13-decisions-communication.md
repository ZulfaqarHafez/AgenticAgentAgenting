# 13. Decisions and communication

A forecast is only valuable if it leads to a better decision. This chapter covers how to turn probabilities into recommendations and how to communicate uncertainty clearly.

## 13.1 The cost–loss model

The simplest decision model. A user can take protective action at cost $C$ (move indoors, delay a concrete pour, reschedule a crane lift). If they don't protect and the adverse event happens, they suffer loss $L$ (with $L > C$).

| | Event happens | Event does not happen |
| --- | --- | --- |
| **Protect** | $C$ | $C$ |
| **Don't protect** | $L$ | 0 |

Expected expense of not protecting is $pL$; of protecting is $C$. **Protect when**

$$p > \frac{C}{L}$$

The threshold depends on the **user**, not the forecast.

**Worked example.** Moving an outdoor event indoors costs SGD 500 (venue fee, logistics); being rained out costs SGD 5,000 (refunds, damaged equipment). Threshold $= 500/5000 = 0.10$. This organiser should move indoors at a 10% chance of disruptive rain. A different user with $C/L = 0.6$ should accept quite a high risk before acting.

**Implication for agents:** ask (or infer) the user's costs. A good recommendation states the probability, the user's threshold, and the conclusion: "25% chance of heavy rain during your event; for your costs the break-even is about 10%, so moving indoors is the better bet."

### Partial protection and multiple actions

With several actions (do nothing, rent tents, move indoors, cancel), each with its own cost and residual loss, choose the action that minimises expected expense:

$$a^* = \arg\min_a \Big[C_a + \sum_s P(s)\,L_a(s)\Big]$$

over weather scenarios $s$ (for example dry, light rain, heavy rain with lightning).

## 13.2 Economic value of a forecast system

How much a forecast system saves, relative to climatology and a perfect forecast, for a user with a given $C/L$:

$$V = \frac{E_{clim} - E_{fcst}}{E_{clim} - E_{perfect}}$$

per occasion (normalising by $n$):
- $E_{clim} = \min(C,\ \bar o L)$: always protect or never protect, whichever is cheaper given the base rate $\bar o$.
- $E_{perfect} = \bar o\,C$: protect only when the event happens.
- $E_{fcst} = \dfrac{(a + b)\,C + c\,L}{n}$: pay $C$ on every "yes" forecast and $L$ on every miss (using the contingency table from chapter 12 at the user's decision threshold).

$V = 1$ is perfect, $V = 0$ no better than climatology, $V < 0$ worse than using climatology.

**Worked example.** Contingency table $a = 30$, $b = 20$, $c = 10$, $d = 40$; $C = 2$, $L = 5$ ($C/L = 0.4$, base rate 0.4):
- $E_{clim} = \min(2,\ 0.4 \times 5) = 2.0$
- $E_{perfect} = 0.4 \times 2 = 0.8$
- $E_{fcst} = (50 \times 2 + 10 \times 5)/100 = 1.5$
- $V = (2.0 - 1.5)/(2.0 - 0.8) = 0.42$

For a user with a much lower $C/L$ (say 0.1), climatology already says "always protect", and the same forecast can have negative value because its misses are expensive. **The value of a forecast depends on who uses it.** For probability forecasts, each user should apply their own threshold, which gives the best value across all users (the "envelope" of value curves).

## 13.3 Timing decisions: act now or wait?

Forecasts improve as the event approaches. Waiting for a better forecast is worthwhile if:
1. the decision can still be changed later,
2. costs of a late decision are not much higher than an early one, and
3. the forecast is likely to change meaningfully.

A simple rule: if the current probability is far from the user's threshold, decide now. If it is close to the threshold and the lead time is long, recommend waiting until a stated time (for example "check again at 11:00; the radar picture will be clearer"), with the deadline set by when the action must be taken.

## 13.4 Thresholds and impact-based forecasting

Weather matters through impacts, which depend on exposure and vulnerability:
- Same rainfall, different impact: 30 mm/h is a nuisance in a park but floods a known low-lying road.
- **Impact-based** messages say what will happen and what to do ("heavy rain may cause flash floods in low-lying areas; avoid underpasses"), not just the numbers.
- **Risk matrix**: likelihood × impact, commonly 4 × 4 (very low to high likelihood; minimal to severe impact), mapping to green/yellow/amber/red levels.

## 13.5 Communicating uncertainty

### Principles

1. **Give the probability as a number** for decision makers; add words for general users.
2. **State the event precisely**: what, where, when, how much ("≥ 10 mm/h at Marina Bay between 15:00 and 18:00").
3. **Give the reason** in one line ("storms are building over Johor and moving south").
4. **State confidence and what could change it** ("low confidence in timing; storms could form earlier if sea breezes converge sooner").
5. **Give the most likely and the reasonable worst case** for high-impact events.
6. **Point to official warnings** when relevant.
7. **Do not hide disagreement** between sources; say it and explain how it was weighed.

### Verbal probability scale

Words are interpreted inconsistently; if used, pair them with numbers and use them consistently. One widely used scale (adapted from the IPCC):

| Term | Probability |
| --- | --- |
| Virtually certain | > 99% |
| Very likely | > 90% |
| Likely | > 66% |
| About as likely as not | 33–66% |
| Unlikely | < 33% |
| Very unlikely | < 10% |
| Exceptionally unlikely | < 1% |

### Frequency framing

"On 3 out of 10 days like this, it rains during your event" is often understood better than "30%".

### Common communication errors to avoid

- Presenting the ensemble mean rainfall as "the forecast".
- Saying "it will rain" when the probability is 60%.
- Implying spatial precision a model cannot give ("rain at 15:20 at your block").
- Mixing up the probability of rain somewhere in Singapore with the probability at the user's location.
- Calling a classifier's confidence a chance of rain (chapter 09).

## 13.6 Explanation template for the Writer agent

```
Recommendation: <action> (<one-line reason>)

Chance of <event, threshold> at <place> between <times>: <p>% (<verbal term>)
Your break-even: about <C/L>% → <conclusion>.

Why: <physical reason from diagnosis>
Sources: <n> sources; <agreement summary>; trusted most: <source> (best recent accuracy here).
Confidence: <high/medium/low> because <reason>. Could change if <trigger>.
Check again: <time>, when <new information> is available.
Official: <active NEA/PUB warning, or "no active warnings">.
```

Every number in the message must come from the structured forecast object, not be generated by the language model.
