# Verlane Idea

## Summary

Verlane is a local-first agentic coding runtime designed to help language models complete long-running software-engineering tasks more reliably.

The central hypothesis is that a large part of the gap between raw model capability and strong end-to-end coding performance can be reduced by improving the runtime around the model rather than by training a new model first.

Verlane therefore treats the language model as an interchangeable reasoning engine and moves persistent knowledge, verification, task state, context management, tool execution, recovery, and execution policy into the runtime.

The initial motivation is to make capable local models substantially more useful, but the runtime itself is not intended to be local-model-only. A stronger hosted model should generally retain a higher capability ceiling, while still benefiting from the same disciplined runtime mechanisms where they address failures that are independent of raw model intelligence.

## Problem

Local language models offer important advantages:

- inference can remain on the user's machine;
- there is no dependency on hosted-model request limits or provider availability;
- long-running work is not constrained by per-request pricing in the same way as hosted inference;
- users gain substantially more control over how code and project context are handled.

However, using a capable local model directly for coding still has major weaknesses. Smaller models can repeatedly rediscover the same technical knowledge, rely on stale information, lose important state during long tasks, waste context on conversation history, loop on failed approaches, and make poor decisions when the surrounding runtime leaves too much orchestration to the model itself.

The original motivation for Verlane came from this mismatch: a local model may be capable of tool use, reasoning, English, and programming, yet still produce a much worse end-to-end coding experience than expected because the runtime does not sufficiently structure its work.

The same class of runtime failures can also affect stronger models. Better reasoning and broader knowledge can reduce their frequency, but do not remove problems such as stale external information, lost task state, unverified assumptions, weak execution discipline, or insufficient validation.

## Evolution of the Idea

### Initial hypothesis

Build a small specialized model, roughly in the 7B class, trained primarily for:

- English;
- expert tool use;
- expert web search;
- high-effort reasoning.

The model would not need to contain broad programming knowledge. Instead, it would research what it needed during a task and use external tools to learn and implement solutions.

### Second hypothesis

A specialized model would still repeatedly relearn the same information across tasks. This led to the idea of persistent caches at different scopes so that acquired knowledge could be reused.

The intended behavior became:

```text
Retrieve cached knowledge
        ↓
Verify that it still applies
        ↓
Research only when necessary
        ↓
Implement
        ↓
Persist newly validated knowledge
```

### Current hypothesis

The runtime, rather than a newly trained model, is the core product.

Existing local models already provide enough of the required foundation to test the idea: they can reason, use tools, understand code, and interact in English. The highest-value initial experiment is therefore to build the runtime first and measure how much it improves the performance of an existing local model.

The runtime should remain model- and provider-agnostic in principle. Local inference is the primary initial use case, not a permanent architectural boundary. If the runtime successfully removes failure modes that are external to raw model intelligence, stronger hosted models should also benefit, although the relative improvement may be smaller because those models begin from a stronger baseline.

A specialized model remains a possible future direction, but only if runtime evaluation reveals a recurring model-level bottleneck and Verlane has collected enough real execution data to justify training or fine-tuning one.

## Core Insight

Verlane should move as many repeatable and deterministic responsibilities as possible out of the language model and into software.

The model should spend its limited reasoning capacity on decisions that genuinely require reasoning. The runtime should handle policy, state, bookkeeping, validation gates, persistence, and deterministic inspection wherever practical.

The product is therefore not simply "a local coding agent with memory." Its intended value is a disciplined execution environment that reduces the number of ways a model is allowed to fail because of weak process, missing state, stale knowledge, or unverified execution.

Verlane is not intended to erase differences between models. Model quality still determines important capabilities such as reasoning depth, judgment, code generation quality, and novel problem solving. The runtime is intended to make better use of whatever capability the selected model already has.

## Model Failure Surface

A useful way to reason about Verlane is to separate raw model capability from the surrounding failure surface of an agentic coding task.

Poor output can come from several distinct classes of failure:

### Specification failure

The agent may solve the wrong problem because the desired outcome, constraints, or definition of done are incomplete or misunderstood.

Project documentation can reduce this risk, but useful specification evidence can also come from the user's request, existing code, tests, issues, architecture decisions, configuration, and repository conventions.

### Knowledge failure

The agent may not know a library, may rely on stale information, may hallucinate an API, or may search poorly and use incorrect technical material.

Verified reusable knowledge, version-aware research, provenance, and evidence are intended to reduce this class of failure.

### Assumption failure

The agent may make a plausible but unsupported assumption about the project, environment, architecture, desired behavior, root cause, or dependency contract and then build correct-looking work on top of a false premise.

Documentation helps when the relevant fact has already been recorded, but documentation alone cannot eliminate this problem. Important assumptions should be made explicit and checked against available evidence whenever practical.

In particular, high-impact decisions should not silently depend on unresolved low-confidence assumptions when the runtime can inspect the repository, execute a check, consult authoritative documentation, or ask for clarification when genuinely necessary.

### Reasoning and planning failure

The agent can possess correct information and still choose a poor design, optimize the wrong thing, fix a symptom instead of a root cause, or construct an ineffective plan.

This is where model capability remains especially important. Runtime structure can reduce the consequences through incremental planning, evidence, feedback, and re-evaluation, but it cannot completely replace reasoning quality.

### Context and observation failure

The agent may fail because the right information is not in front of it: an important file was never inspected, a previous decision was lost, stale state was presented, or context compaction removed something important.

Durable task state, repository inspection, context reconstruction, checkpoints, and targeted retrieval are intended to reduce this class of failure.

### Execution and validation failure

A correct plan can still be implemented incorrectly. The agent may miss a call site, introduce a syntax error, run a command in the wrong environment, break an integration, or declare success without testing the actual behavior.

Execution should therefore produce evidence. Compilation, tests, linting, runtime checks, diff inspection, and other project-appropriate validation should be preferred over trusting the model's own claim that the work is complete.

### The broader objective

These failure classes suggest a broader product objective:

> Reduce the number of ways the model is allowed to be wrong before relying on the model to be smarter.

Where software can verify a fact, preserve state, enforce a gate, inspect an environment, detect repetition, or validate an outcome, Verlane should prefer that over spending model intelligence on avoidable uncertainty.

What remains for the model should increasingly be the work that benefits most from language-model capability: reasoning, judgment, synthesis, code generation, and novel problem solving.

## Intended Execution Model

The current conceptual execution loop is:

```text
Task
  ↓
Inspect environment
  ↓
Retrieve relevant memory
  ↓
Verify applicability
  ↓
Need fresh knowledge?
  ├── No ─────────────────────┐
  └── Yes → Research          │
             ↓                │
           Distill            │
             ↓                │
           Persist ───────────┘
             ↓
            Plan
             ↓
         Implement
             ↓
            Test
             ↓
       Fix / iterate
             ↓
      Distill learnings
             ↓
       Persist memory
             ↓
            Done
```

The exact protocol is not yet a finalized system design. The important idea is the ordering constraint: remembered technical knowledge must not be treated as automatically valid merely because it exists.

The conceptual loop also does not imply that every task follows one rigid linear sequence. New observations can invalidate assumptions, reveal missing knowledge, or require re-planning. The runtime should eventually be able to move back to the appropriate verification or research step rather than blindly continue from an invalid premise.

## Verified Memory

Persistent memory is one of the main product ideas behind Verlane.

The current conceptual scopes are:

### Session memory

Temporary information useful only during the current execution, such as hypotheses, intermediate results, current failures, and temporary observations.

### Project memory

Knowledge that belongs to a specific repository, such as architecture conventions, commands, dependency choices, repository-specific workflows, and project decisions.

### User memory

Stable user preferences that can apply across projects, such as preferred package managers or tooling conventions, unless a project explicitly overrides them.

### Global knowledge

Reusable technical knowledge about languages, libraries, protocols, frameworks, APIs, and tools.

When scopes conflict, more specific context should take precedence. Conceptually:

```text
Project context > User preference > Global default
```

Global technical memory should not be treated as an unstructured notebook. Useful entries are expected to carry enough metadata to determine whether they remain applicable, including information such as versions, provenance, verification time, confidence, and evidence.

## Verify Before Implement

A central principle is:

> Cached technical knowledge is a retrieval hint, not proof that the knowledge still applies.

For example, if Verlane remembers how to use a library, the runtime should first determine which version the current project actually uses. If the stored knowledge applies to that version, expensive relearning can be skipped. If it does not apply, the agent should research the relevant version and update its knowledge.

Verification should use deterministic local evidence whenever possible. Reading a lockfile, manifest, configuration file, installed package metadata, or source tree is preferable to asking the language model to infer information that software can determine directly.

The existence of a newer stable dependency version also does not automatically justify changing the project. The installed or locked version is part of the project's current contract. Dependency upgrades should be treated as separate decisions rather than silently folded into unrelated implementation work.

The same principle extends beyond cached library knowledge. Important assumptions about the repository or task should be supported by evidence when their correctness materially affects the implementation.

## Long-Running Tasks and Context

Verlane is intended to support tasks that may run for hours without requiring the entire historical conversation to remain in the model context.

Conversation history should not be the source of truth for task execution.

Instead, the runtime should maintain durable structured state representing concepts such as:

- the original task;
- the current objective;
- completed work;
- current subtask;
- files changed;
- known facts and evidence;
- assumptions and their confidence or verification state;
- failed attempts;
- test results;
- unresolved questions;
- useful memory candidates.

The context presented to the model can then be reconstructed from current state, relevant repository information, and relevant memory rather than from an ever-growing transcript.

This is the conceptual basis for reliable checkpointing, context compaction, process recovery, and task resumption.

## Local-First, Not Local-Only

The initial product direction is local-first rather than cloud-first, but local inference is not intended to be a permanent restriction on which models Verlane can use.

The language-model inference path should be able to run using a local provider, because local execution directly addresses the original motivation around privacy, control, request limits, availability, and long-running work. This should remain a first-class use case rather than an afterthought.

At the same time, the runtime should conceptually allow other model providers. If a stronger hosted model has better reasoning, judgment, or generation capability, Verlane should be able to preserve that advantage while still providing durable state, verified knowledge, controlled research, execution policy, and validation.

This produces an important distinction:

```text
Local-first != local-only
```

Network access is still expected when research is required, so local inference also does not imply that every operation is offline.

This distinction matters for privacy. Web searches and external requests can still expose information if they are constructed carelessly. Verlane should therefore eventually treat outbound research as a controlled boundary and avoid leaking repository secrets, credentials, or unnecessary private source material.

Likewise, content retrieved from the web should be treated as untrusted data rather than trusted instructions.

These are product principles at this stage; concrete provider support, security requirements, and mechanisms belong to later engineering phases.

## Why the Runtime Is the Product

The most important change in the idea is the separation between model capability and runtime capability.

A model provides reasoning, interpretation, generation, and judgment. The runtime can provide durable memory, verified knowledge reuse, state management, context reconstruction, tool policy, recovery, deterministic environment inspection, assumption tracking, and execution constraints.

This separation has several advantages:

- the model can be replaced without redesigning the whole product;
- local and hosted providers can eventually be supported behind the same product concepts;
- improvements to orchestration can benefit every supported model;
- expensive knowledge acquisition can be amortized across tasks;
- failures can be inspected and measured at the runtime level;
- stronger models can spend more of their capability on reasoning instead of avoidable bookkeeping;
- future training data can be collected from real execution trajectories rather than invented workflows.

The expected outcome is not that all models become equivalent. A stronger model should generally retain a higher ceiling. The intended outcome is that each model operates closer to its useful ceiling because fewer failures are caused by the runtime around it.

## Product Hypotheses

The primary hypothesis to validate is:

> A disciplined runtime with verified reusable knowledge, durable task state, strong context management, explicit assumption handling, and deterministic execution policy can make a capable local model substantially more effective on long-running coding tasks than the same model used through a simpler agent loop.

The important initial comparison is therefore not primarily between different models. It is between the same model operating under different runtime conditions.

A secondary hypothesis follows from the provider-agnostic product direction:

> Runtime mechanisms that eliminate failures external to raw model intelligence should also improve stronger models, even if the relative improvement is smaller than it is for weaker local models.

This secondary hypothesis should not distract the MVP from its original purpose. Local models remain the clearest initial environment in which to test whether Verlane's runtime creates meaningful leverage.

## Early Validation Direction

A particularly useful experiment will test whether memory improves repeated work without introducing stale-knowledge failures.

A conceptual sequence is:

1. Give the agent a task using a library version it has not previously handled.
2. Allow it to research, solve the task, and persist validated knowledge.
3. Give it a different task using the same relevant library version and measure whether useful research is avoided.
4. Give it a task using a materially different version and verify that stale memory is detected rather than blindly reused.

This would test both sides of the idea: reuse and invalidation.

Additional evaluation should eventually distinguish different failure classes rather than reporting only a single task-success score. For example, a failed task caused by stale knowledge is materially different from one caused by poor reasoning or an unclear specification.

Formal benchmarks, metrics, and experimental methodology belong to the Validation Design phase.

## Current Product Direction

The current direction is to build an MVP agentic coding runtime around existing models rather than train a model first.

Local models are the primary initial target because they most directly expose the problem Verlane was created to investigate. The product concepts should nevertheless avoid unnecessary assumptions that would prevent the same runtime from later supporting stronger hosted models.

The MVP should be designed to answer the primary product hypothesis as quickly and cleanly as possible. Features that do not directly contribute to that experiment should be treated cautiously until requirements and MVP scope are formally defined.

## What Is Not Decided Yet

This document records the idea, not the architecture.

The following are intentionally unresolved:

- implementation language;
- runtime architecture;
- storage technology;
- exact state-machine design;
- provider abstraction design;
- tool protocol and sandbox architecture;
- memory schema and retrieval implementation;
- assumption representation and verification mechanics;
- context-management algorithms;
- exact provider support in the MVP;
- precise security model;
- benchmark suite and success thresholds.

Those decisions belong to subsequent software-engineering phases.

## Next Step

The Idea phase is complete once this foundation is reviewed and accepted.

The next phase is **Requirements & Constraints**, where the concept will be translated into explicit system behavior, guarantees, boundaries, non-functional requirements, invariants, security assumptions, exclusions, and measurable success criteria before architecture or technology choices are made.
