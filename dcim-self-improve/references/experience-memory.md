# Short route memory

One record format serves action, experience and reflection. Required fields:
type, stage, module, route, scope (general/process), status
(supported/uncertain/refuted), condition, operation, observation, next_test,
evidence IDs. Process scope also needs exact technology (process/release/stack).
Each text is at most 240 characters; each commit has at most six entries and each
entry at most eight evidence IDs. Runtime adds identity, round and review binding.

Builder proposes; Analyst reviews and commits action/experience before Reflect.
Reflect writes one reflection before the next task. No separate compression agent
or second summarization pass. Exact geometry/code/logs stay in immutable objects.

Read by stage -> module -> route with a bounded result count. Non-active routes
are omitted from default detail reads; explicitly selecting a route exposes its
scoped knowledge. Route lifecycle: active, deferred, refuted-in-scope, superseded.
Correct a conclusion with a new entry naming supersedes. Old revisions remain;
default reads return current entries. General methods do not inherit node-specific
numbers. Repeated/no-new findings refresh the review disposition without essays.
