# Looking at what is on the person's screen right now

The person wants you to look at their screen. First, capture a screenshot into your media directory using `tools.OS.screenshot` with all-zero coordinates for a full grab and an explicit `path` under your media directory (its location is stated in your permissions above). On the next cycle, you will see the TOOL_RESULT with the saved path. Then call `abilities.look_at` with that `source` and a precise `question` tied to what the person asked. On the cycle after, reply with `say`.
