# Looking back at past conversations or scheduled events

Look back. Past conversations are held by day (`abilities.recall_history` with `date` as YYYY-MM-DD). Scheduled events live on the calendar (`abilities.check_calendar` with `date` as YYYY-MM-DD or YYYY-MM). Resolve the date from the conversation and the current time, then look it up. If the date is unclear, ask with `say` first. When the TOOL_RESULT comes back on the next cycle, reply with what you found.
