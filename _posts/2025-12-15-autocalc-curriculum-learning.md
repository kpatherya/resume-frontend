---
layout: post
title: "AutoCaLC: Teaching the Teacher"
date: 2025-12-15 17:00:00 +0100
description: my causal curriculum learning project from FA25
excerpt: AutoCaLC treats curriculum design as a meta-learning problem. A teacher agent learns which environmental interventions to hand a PPO student next, using the student's own generalization performance as its reward signal.
---
Everyone in robot learning has run into the adaptation gap. A policy trained in simulation does beautifully in simulation, then meets a slightly heavier block or a slightly slicker floor and falls apart.<sup>1</sup> The usual fix is curriculum learning: start the agent on easy versions of the task and gradually make life harder.<sup>2</sup>

That works, but almost every implementation I read used a fixed schedule or a hand-written heuristic. Which raises the obvious question: how would you ever know if the agent spent too long on a task it had already solved, or moved off a hard one too early? The curriculum is a policy too. Why not learn it?

That's AutoCaLC - **Auto**mated **Ca**usal **L**earning **C**urriculum. A teacher agent learns to pick environmental modifications for a student agent, and gets rewarded by how well the student generalizes.

### The playground

All of this runs in **CausalWorld**, a physics simulator built around a TriFinger robot.<sup>3</sup> The reason I care about CausalWorld specifically is that it exposes *interventions* - you can change the mass of a block, the friction of the floor, the color of an object, mid-experiment. These are concrete instantiations of Pearl's $do()$ operator.<sup>4</sup> If an agent trained only on light blocks collapses when the mass goes up, that's evidence its policy was riding a spurious correlation rather than any understanding of the physics.

I used seven interventions throughout:

* **Goal**: moves the target, forcing the agent to reach different parts of the workspace.
* **Mass**: alters the mass of the tool. Heavier means more force to start and stop.
* **Friction**: changes the floor, making objects easier or harder to push and slide.
* **Visual**: changes appearance only. A test of whether the agent is learning from state features that actually matter.
* **Position**: moves the block's starting position.
* **Orientation**: rotates the block without moving it, so the agent has to approach from new angles.
* **Random**: a catch-all combining several of the above (excluding joints, which is a trickier space).

<div style="text-align: center;">
    <img src="/assets/autocalc/causalworld-task-configs.png" width="100%" />
    <em><br>Fig. 1. <b>Interventions in CausalWorld:</b> The agent is rewarded in proportion to the intersection between each block and the goal configuration. From T1 to T4, block size is changed directly through the simulator's built-in interventions.</em>
</div>

### First question: does order matter?

Before building anything clever, I wanted to know whether the *sequence* of interventions changes the outcome at all. Seven interventions means 7! = 5,040 possible orderings. Brute force is already impractical, and it gets absurd quickly - ten interventions would be 3,628,800 sequences.

So I ran four heuristics against each other, all starting from the same pretrained PPO checkpoint, all with the same total training budget.<sup>5</sup> Each one tests the remaining interventions in a separate environment (so the evaluation doesn't contaminate the policy), picks one, trains on it, and repeats until it runs out.

* **None**: no interventions at all. Keep training on the base environment.
* **Random**: uniform sampling from the remaining pool. The control.
* **Greedy**: pick whichever remaining intervention yields the highest average episodic reward right now.
* **Causal-Mismatch**: pick by balancing novelty against learnability.<sup>6</sup>

Causal-Mismatch is the interesting one. For each intervention, I collect trajectories with the current policy, train small ensembles for transition dynamics, reward dynamics, and $\beta$-VAEs over states and actions, then score disagreement as the sum of ensemble standard deviations. That disagreement is an implicit signal of *epistemic uncertainty* - where the agent's internal model of the world is misaligned with reality - without having to discover a full structural causal model, which is intractable at this scale.<sup>7</sup> The final score combines it with reward:

$$\text{Unified} = \alpha \cdot CM_{norm} + (1-\alpha) \cdot Reward_{norm}$$

with $\alpha = 0.5$, weighting novelty and learnability equally.

The three curricula picked genuinely different orders, which told me the selection rules were doing something:

| Stage | Random | Greedy | Causal-Mismatch |
|---|---|---|---|
| 1 | random | position | position |
| 2 | visual | goal | friction |
| 3 | position | friction | visual |
| 4 | goal | visual | mass |
| 5 | friction | mass | random |
| 6 | angle | random | goal |
| 7 | mass | angle | angle |

### What the baselines showed

Training *None* with no interventions produced the highest mean episode reward and hit the 500-step episode cap almost immediately. It had mastered the default environment. It also had a 0% success rate at final evaluation. It was optimizing reward, not the task.

All three curricula took a reward hit the moment the first intervention landed, and then diverged. Causal-Mismatch ended with the highest policy standard deviation and the steepest entropy reduction of the four - it explored broadly across regimes while committing decisively within each one.

<div style="text-align: center;">
    <img src="/assets/autocalc/policy_std.png" width="85%" />
    <em><br>Fig. 2. <b>Policy standard deviation across all four heuristics:</b> Green dashed lines mark curriculum stage boundaries. All baselines start from the same pretrained checkpoint. Causal-Mismatch climbs fastest, which is what you would expect from the curriculum that exposes the policy to the most diverse experience.</em>
</div>

But then the generalization sweep across CausalWorld's standardized protocols (P0-P11) delivered the result I did not want:

| Rank | Baseline | Integrated success | vs. None |
|---|---|---|---|
| 1 | Random | 0.2334 | +41.3% |
| 2 | Causal-Mismatch | 0.1987 | +20.3% |
| 3 | Greedy | 0.1884 | +14.0% |
| 4 | None | 0.1652 | — |

**Random won.** A principled, ensemble-based novelty measure lost to picking interventions out of a hat. Causal-Mismatch was the only method to reach a 100% success rate at final evaluation, so it was learning something real about *completing the task* rather than maximizing score - but it didn't generalize best.

Two honest caveats. The random baseline was run with a single seed; a proper comparison needs mean and variance over many orderings, and a different seed might well have produced a different winner. And Causal-Mismatch is sensitive to $\alpha$, which I fixed at 0.5 with no tuning.

Still, the takeaway pointed somewhere useful: if random ordering can beat a hand-designed heuristic, there are certainly good sequences among those 5,040 that no fixed rule will find. What if the selection rule could learn?

### The AutoCaLC framework

The student is a PPO agent with a two-layer MLP, 64 units each, solving the CausalWorld pushing task.<sup>8</sup> The teacher is a DQN that picks which of the seven interventions to apply next.<sup>9</sup>

<div style="text-align: center;">
    <img src="/assets/autocalc/meta-structure.png" width="80%" />
    <em><br>Fig. 3. <b>The teacher-student loop:</b> The teacher observes the student's learning state, emits a meta-action that reconfigures the physics engine, and receives a meta-reward from the student's performance in a fixed validation set.</em>
</div>

The teacher lives in a meta-level MDP:

**Meta-state.** For each of the seven interventions I compute two numbers: the causal-mismatch score (how inconsistent the student's dynamics ensembles are under that intervention) and the average reward the student gets when it briefly runs its current policy there. Both are normalized independently across the seven, then concatenated into a fixed 14-dimensional vector. That's the teacher's entire view of the student.

**Meta-action.** One of seven interventions.

**Meta-reward.** The student's average reward over ten fixed validation environments. Critically, these environments are *not* affected by the teacher's choice, so the feedback signal isn't gamed by picking an easy intervention.

Training runs in meta-episodes: the teacher observes, picks an intervention, the student trains for 5,000 timesteps in the modified environment, the student is evaluated on the validation set, and the tuple $(S_{meta}, A_{meta}, R_{meta}, S'_{meta})$ goes into the teacher's replay buffer. Fifty meta-episodes, so 250,000 student timesteps and fifty curriculum decisions.

The expensive part is that each teacher decision costs a full 5,000-step student training run. You cannot afford a sloppy exploration schedule at that price, so I used three phases: pure exploration ($\epsilon = 1.0$) for the first 5 meta-episodes, decay from 0.8 to 0.2 over the next 30, then a slow decay to 0.05 over the final 15. A 50K-transition replay buffer absorbs the non-stationarity of a student whose policy is changing underneath the teacher, and the target network uses a soft update with $\tau = 0.005$. Every run starts from the same pretrained PPO checkpoint, trained 5,000 steps on the base environment.

I went in with four hypotheses:

* **H1**: AutoCaLC hits perfect validation success more often than myopic approaches like Greedy.
* **H2**: AutoCaLC accrues *lower* reward in early meta-episodes, because the teacher starts at 100% exploration and makes bad calls before it knows anything.
* **H3**: AutoCaLC is more resilient across the seven interventions.
* **H4**: Most importantly, AutoCaLC does better across the benchmark protocols than the specialized baselines.

### What actually happened

H2 held, which is the least impressive kind of correct. The teacher does start badly, exactly as a fully exploring DQN should.

H4 did not hold. Across the P0-P11 benchmark sweep, AutoCaLC scored near zero on most protocols, well below the heuristics and below the pretrained checkpoint it started from. The learned curriculum was worse than picking at random.

<div style="text-align: center;">
    <img src="/assets/autocalc/benchmark_radar_plot.png" width="80%" />
    <em><br>Fig. 4. <b>Benchmark performance across protocols P0-P11:</b> Each axis is a different environmental configuration. No method dominates, and the spikiness is the real story - these policies are winning individual protocols rather than generalizing across them.</em>
</div>

I do not think this makes the idea wrong, but I think it makes the *budget* wrong, and it's worth being specific about why:

**Fifty decisions is nothing.** A DQN needs thousands of transitions to learn a useful Q-function. The teacher got fifty, and burned the first five on pure exploration. It never had the data to distinguish a good intervention from a lucky one.

**The meta-reward is noisy.** Average validation reward after 5,000 student timesteps is a high-variance measurement. Two identical teacher actions can produce visibly different meta-rewards, so the teacher is fitting a Q-function to mostly noise.

**The student is a moving target.** Standard DQN assumes a stationary environment. Here the "environment" includes a student policy that changes every meta-episode. The replay buffer stores transitions describing a student that no longer exists.

**The benchmark rewards specialists.** Look again at the radar plot: every method has spikes. Greedy owns P0 and P4, Causal-Mismatch owns P8, Random owns P7. Nothing covers the whole space. An integrated score across protocols may be rewarding lucky specialization more than genuine robustness, which makes it a shaky target for the teacher to optimize toward.

### Where this goes

The cleanest fix for the sample-efficiency problem is to stop making the teacher learn from scratch. Pretrain a set of teachers, each one specialized to a particular intervention, then put a meta-controller above them - a **dean** - whose only job is to pick which teacher is most appropriate for the student's current state. The student learns through guided policy distillation, with PPO loss plus a KL term between student and selected teacher.

<div style="text-align: center;">
    <img src="/assets/autocalc/metarl-merged-diagram.png" width="100%" />
    <em><br>Fig. 5. <b>Left:</b> the current teacher-student loop. <b>Right:</b> the proposed dean architecture, where a meta-controller selects among pretrained teachers and the student learns by distillation. The dean's action space is small and its reward is the student's validation improvement.</em>
</div>

The dean's action space is small, its state is the teachers' collective output, and its reward is the student's improvement on the validation set. That's a far more tractable learning problem than what I asked the teacher to solve here.

Two other things I'd change. Run the random baseline across many seeds so the comparison is against a distribution rather than one draw. And replace the integrated protocol score with something that explicitly penalizes spiky, specialist performance - if the goal is robustness, the metric should say so.

**Coda.** This project was conducted at Georgia Tech in Spring-Fall 2025, with Batuhan Altunda, Yu Wang, Idris Wibowo, and Dr. Matthew Gombolay. The full implementation is on [GitHub](https://github.com/kpath1999/causal-core-su25).
