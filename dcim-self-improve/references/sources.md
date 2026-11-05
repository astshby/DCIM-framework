# Inputs and provenance

The generic configuration, module contract, history and geometry helpers derive
from improve 1. Evidence parsing and stage/route retrieval principles derive from
improve 2. The fixed 12FFC seed was removed from the active tree; its prior version
remains in repository Git. Neither reference directory is modified or synchronized.

Agents create private configuration with `configure.py`, optionally --from-config.
Paths resolve against the configuration file. Project precision, ratio accounting,
process/release/stack and electrical conditions remain explicit. Existing configs
using project/input_files are supported; old native12/warm-start keys need deliberate
migration, not silent reuse. No node-specific compiler filenames are prescribed.

`learn.py` accepts captured geometry JSON or GDS (optional gdspy). Context identifies
module/process/release/stack/source_run. Keep reference-only observations distinct
from qualified implementation. Proprietary inputs stay outside the package.
