---
layout: post
title: "Mastering Robotic Arm Manipulation with Deep Reinforcement Learning"
date: 2024-12-08 18:22:08 17:00:00 +0100
description: my advML project from FA24
excerpt: A comparison of three reinforcement learning algorithms - A2C, DQN, and PPO - to the task of robotic arm manipulation for pick-and-place tasks using the Kuka environment simulation on PyBullet.
---
Robotic manipulation, combining robotics and machine learning, aims to develop adaptive systems for tasks like grasping and assembling. This project applies reinforcement learning (RL) algorithms to train a robotic arm for pick-and-place operations using the PyBullet physics engine. Advantage Actor Critic (A2C), Deep-Q-Networks (DQN), and Proximal Policy Optimization (PPO) are evaluated and compared in terms of sample efficiency, stability, and task completion rates.

**Overview**. The Kuka environment in PyBullet simulates a robotic arm for pick-and-place tasks with realistic physics. It is open-source, models real-world systems, and balances complexity with tractability for RL research. This environment serves as a testbed to compare RL approaches like A2C, PPO, and DQN (value vs. policy, on vs. off policy), helping researchers choose algorithms for similar robotics tasks and inform future development. The agent can choose from 7 actions – move in x-direction (+/-), y-direction (+/-), adjust vertical angle (up/down), or do nothing. Velocity for each direction is equal. A ‘height hack’ is leveraged, where the gripper automatically moves down for each action. As part of the reward structure, the agent receives a reward of +1 if an object is lifted above a height of 0.2 at the end of the episode. Lastly, the environment provides (48, 48, 3) RGB images as input, making way for convolutional neural networks (CNNs) to decode an optimal policy through purely visual input.

### Literature Survey

**Advantage Actor Critic (A2C)**. This algorithm combines value-based and policy-based approaches, making it suitable for discrete and continuous action spaces. A2C learns a value function and a policy simultaneously, potentially leading to more stable and efficient learning in complex, high-dimensional state spaces. It employs a shared network architecture with convolutional layers feeding into separate policy and value function outputs. The inclusion of an entropy regularization term improves exploration by discouraging premature convergence to suboptimal policies.

