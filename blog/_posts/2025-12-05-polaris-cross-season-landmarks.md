---
layout: post
title: "POLARIS: Finding the Same Landmark in a Different Season"
date: 2025-12-05 17:00:00 +0100
description: my vision-language project from FA25
excerpt: POLARIS is a hierarchical pipeline that matches landmarks across seasons. It fuses global vision-language embeddings, open-vocabulary detection, depth consistency, and geometric verification to separate the permanent parts of a scene from the seasonal noise.
---
Most mapping systems carry a quiet assumption: the world today looks like it did when the map was recorded. Outdoors, that assumption falls apart fast. Trees drop their leaves, snow covers the sidewalk, a facade gets scaffolded, and the sun sits somewhere else in the sky. A robot that drove through a place in October can fail to recognize it in January.<sup>1</sup>

This matters most where GPS is unreliable or too coarse - urban canyons, tunnels, dense tree cover - and the vehicle has to fall back on its camera.<sup>2</sup> Nobody is going to rescan an entire city every season just to keep a map usable. If we want *long-term autonomy*, the map has to be built once and stay useful all year. That's the idea behind what people call **forever maps**.

POLARIS is my attempt at a small, tractable slice of that problem: **cross-temporal landmark matching**. Given a query RGB-D frame from one season, can I retrieve the matching frame from a map built in another season, and can I say which parts of the scene are *invariant* (buildings, fences, poles) versus *temporal* (snow piles, foliage, puddles)?

<div style="text-align: center;">
    <img src="/assets/polaris/pair_005_comparison.png" width="95%" />
    <em><br>Fig. 1. <b>The problem in one image:</b> The same garden shed in January and April. The pixels barely agree, but the shed, the roofline, and the tree trunks do. POLARIS tries to match on the second set of things.</em>
</div>

### Why the usual approaches struggle

Today's methods sit at two extremes. Traditional geometric methods use local features like SIFT or ORB, which live on texture and edges - exactly what snow erases and what a low winter sun washes out.<sup>3,4</sup> Global appearance-based retrieval goes the other way: it summarizes the whole frame into a single vector, which survives seasonal change better but suffers from perceptual aliasing.<sup>5</sup> Every snowy road looks like every other snowy road.

Semantic approaches help, but most of them use closed-set detectors trained on a fixed list of categories.<sup>6</sup> Outdoor scenes are full of things those lists never anticipated: a bare hedge, a snow pile, a wet patch of gravel. If you can't name it, you can't down-weight it.

What was missing, to me, was a way to use all three signals at once - global context, object-level semantics, and 3D geometry - so the system could lock onto the stable skeleton of a scene and ignore the rest.

### The dataset and the preprocessing

I used **ROVER**, specifically the *Garden Large* sequence, which captures the same outdoor environment in winter and autumn.<sup>7</sup> Foliage loss, snow cover, lighting shifts - it's a hard sequence on purpose, and it comes with aligned depth, which I needed.

Each season has roughly 2,000 keyframes. Two preprocessing steps run before anything else:

**Keyframe selection.** Consecutive frames in a driving sequence are near-duplicates. I compute HSV histograms $H$ for frames $f_t$ and $f_{t+1}$ and keep a frame only if the histogram intersection $I(H_t, H_{t+1}) < \tau_{hsv}$, with $\tau_{hsv} = 0.9$. This cuts the search space by roughly $100\times$ without throwing away distinct viewpoints.

**Open-vocabulary detection.** I use OWL-ViT to propose regions of interest.<sup>8</sup> Unlike a closed-set detector, it takes text prompts, so I tailored the prompt set to the environment: *tree*, *house*, *fence*, *bench*, *path*. Open-vocabulary detection is noisy, so the thresholds are not uniform. High-frequency, ambiguous classes like *tree* and *house* get a stricter confidence threshold ($\tau_{\text{high}} = 0.2$) to stop them from flooding the candidate set. Distinct, structurally informative landmarks like *fence* and *bench* get a looser one ($\tau_{\text{low}} = 0.1$) to preserve recall. Anything matching *snow*, *mud*, or *shadow* is suppressed outright - those are the things I explicitly do not want to localize against.

### The pipeline

POLARIS is a four-stage, coarse-to-fine pipeline. For a query frame $Q$ and a candidate frame $C$, the total score is a weighted sum:

$$S_{total}(Q, C) = w_v S_{vis} + w_s S_{sem} + w_d S_{depth} + w_g S_{geom}$$

with $w_v = 0.3$, $w_s = 0.2$, $w_d = 0.2$, and $w_g = 0.3$ after empirical tuning.

<div style="text-align: center;">
    <img src="/assets/polaris/polaris-architecture.png" width="100%" />
    <em><br>Fig. 2. <b>The POLARIS pipeline:</b> HSV keyframe filtering, OWL-ViT open-vocabulary detection, FastVLM embeddings, depth validation, and ORB + RANSAC geometric verification, producing the top-5 retrieved frames for a query.</em>
</div>

**1. Visual similarity.** FastVLM produces a global embedding $E \in \mathbb{R}^{512}$ per frame, and the score is plain cosine similarity.<sup>9</sup> This is the coarse filter: it tells me which frames are plausibly the same place.

$$S_{vis} = \frac{E_Q \cdot E_C}{|E_Q| |E_C|}$$

**2. Semantic similarity.** Let $L_Q$ and $L_C$ be the sets of unique detection labels in the two frames. The Jaccard index rewards frames that contain the same kinds of things:

$$S_{sem} = \frac{|L_Q \cap L_C|}{|L_Q \cup L_C|}$$

**3. Depth consistency.** For every matched region I take the median depth $\tilde{d}$ and score consistency as a ratio, which keeps it scale-invariant:

$$S_{depth} = \frac{\min(\tilde{d}_Q, \tilde{d}_C)}{\max(\tilde{d}_Q, \tilde{d}_C)}$$

Matches above $0.7$ get labelled **invariant**. This is the step that actually separates the permanent structure from the seasonal dressing - a snow bank sitting a meter in front of a wall does not agree with that wall in depth.

**4. Geometric verification.** For the survivors, I extract ORB keypoints *inside the bounding boxes of invariant objects only*, estimate a homography with RANSAC, and use the inlier ratio as the score. Restricting keypoints to invariant regions is the whole point - it is why this stage does better here than running ORB over the full frame.

### How I evaluated it

ROVER does not ship object-level bounding box annotations for my prompt set, so mAP was off the table. Instead I manually inspected the top-5 retrievals for physical overlap with the query scene, and used **average pairwise IoU** as a proxy for match quality. For each detected object $b_{q,i}$ in the query, I find the best-overlapping box in the retrieved frame:

$$\text{Overlap} = \frac{1}{N} \sum_{i=1}^{N} \max_{j} \text{IoU}(b_{q,i}, b_{r,j})$$

This asks a narrow question - do objects land in spatially similar places, assuming roughly aligned viewpoints - but it is measurable and it is honest about what it measures.

I ran queries both directions: autumn as the map with winter queries, then winter as the map with autumn queries.

### Baselines

**Baseline A - global visual and semantic retrieval.** FastVLM embeddings plus the Jaccard semantic score, weighted toward appearance: $S_A = 0.7 \cdot S_{vis} + 0.3 \cdot S_{sem}$. I expected it to handle general scene similarity well and to get confused by places that look alike.

**Baseline B - geometric-only matching.** ORB keypoints inside detection boxes, RANSAC homography between every query-candidate detection pair, scored by the confidence of the fit. I expected this to collapse under snow, and it did.

### Results

| Metric | **Baseline A** | **Baseline B** | **POLARIS** |
|---|---|---|---|
| Mean IoU | 0.2529 | 0.2054 | 0.2451 |
| Std IoU | 0.1068 | 0.0812 | 0.1246 |
| Min IoU | 0.0100 | 0.0887 | 0.0100 |
| Max IoU | 0.4082 | 0.3249 | **0.4479** |
| Matches | 6/10 | 1/10 | **7/10** |

POLARIS retrieves the correct scene 7 times out of 10, against 6 for Baseline A and 1 for Baseline B. The geometric-only baseline falling off a cliff is the least surprising result in the whole project: keypoint matching simply does not survive a season change.

The more interesting comparison is against Baseline A. Mean IoU is basically a tie (0.2451 vs. 0.2529), but POLARIS has the highest maximum IoU (0.4479). When the depth and geometry checks fire correctly, they give tighter spatial alignment than semantics alone. On queries like *autumn_0865* and *autumn_0000*, those extra stages prune candidates that looked right and weren't.

### What worked, and what didn't

Qualitatively, the pipeline is at its best when stable man-made structures are in frame - a shed, a fence line, a wall - even when they're partly under snow. It falls over in scenes that are mostly vegetation, where every tree is a plausible match for every other tree and depth alone can't break the tie.

**Is this a success?** Encouraging, not definitive. I can say confidently that the multi-modal approach beats geometric-only matching across seasons. I cannot say there's statistically significant evidence that POLARIS consistently beats the much simpler Baseline A. The gains are real but modest, and they're conditional: geometric verification only refines matches that the upstream semantic proposals already got roughly right.

That conditionality is the honest headline. Three limitations follow from it:

**It inherits the detector's recall.** Everything downstream operates inside OWL-ViT's bounding boxes. Winter changes an object's silhouette - a snow-covered bench stops looking like a bench - and when the detector misses it, the geometry stage has nothing to verify. A missed detection is a missed match even when the geometry would have agreed.

**ORB is still ORB.** I restricted it to stable regions, which helps, but the descriptor itself is fragile under dark-trees-against-bright-snow contrast. Baseline B is the proof.

**It is far too slow for a robot.** Running OWL-ViT and FastVLM in sequence over thousands of frames is an offline batch job, not something that fits on lightweight onboard hardware during live navigation.

### Where I'd take it next

Two directions look most promising to me.

The first is replacing ORB with a **learned matcher**. Transformer-based methods like LoFTR and SuperGlue find dense, context-aware correspondences even when local texture changes completely.<sup>10,11</sup> Most of my current failures are cases where the correct landmark was detected and the verification stage couldn't confirm it - exactly the failure mode these methods are built for.

The second is trading bounding boxes for **pixel-level segmentation** with something like SAM or SegFormer.<sup>12,13</sup> A box around a house in winter contains the house *and* the snow on its roof *and* a slice of sky. A mask would let me separate the snow-covered roof from the unchanged facade and hand the geometric verifier much cleaner input. Coarse boxes are quietly injecting noise into every stage after detection.

**Coda.** This project was conducted at Georgia Tech in Fall 2025, with Samuel Ibidapo and Jacob Blevins. The code is on [GitHub](https://github.com/kpatherya/polaris).
