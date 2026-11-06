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


Persistent learning targets use the same condition / operation / observation /
next_test fields, but serve a different purpose from recent route memory: they
bind reference learning to a task and its required checks. learning_contract.py
retains active goals and latest Analyst outcomes in learning_focus; they do not
age out when memory.select returns its newest eight records. Correct by explicit
supersession. Treat general goals as conditional methods to test, not portable
process qualification. Runtime payloads are in [runtime.md](runtime.md).


## Programmatic promotion and cross-run retrieval

After Analyst commits a current supported/refuted experience, the agent may run:

```sh
python3 RUN/scripts/experience.py --run RUN --ids MEMORY_ID --output RUN/exports/METHOD_VERSION
```

This publishes an immutable experience.json and the referenced artifact closure,
including the source review and available Reflect prompt/reply. Uncertain,
superseded or unreviewed lessons are rejected; evidence must have been inspected
by the source Analyst. A failed review can support a refuted lesson; it cannot
create a successful action. Existing bundles cannot be overwritten.

For a later run set experience_root to the library directory and list explicit
bundle manifests in input_files.experience_root. Initialization verifies all
retained object identities and copies a fixed snapshot. It never writes to that
read-only library. Publish a revised bundle in a new path and explicitly replace
the configured selection; retain old bundles and old runs. At most 16 bundles,
six lessons each, and eight applicable retrieved records bound ordinary context.

workflow context/request supplies role_experience newest first, filtered by
stage/module and exact technology for process scope. General methods may cross
nodes, but every imported record is uncertain/reference-only in the receiver;
source_status remains visible. It cannot count as a locally supported action or
a validated learning goal. Test and review it locally before promoting a new claim.
This is a maintained role-experience library supplied beside role Markdown; static
policy is changed only through a versioned framework revision. Source evidence
bundles may contain private IP and must remain outside the framework Git/ZIP.
