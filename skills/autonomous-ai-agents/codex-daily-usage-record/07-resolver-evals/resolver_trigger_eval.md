# Resolver Trigger Eval

These prompts should trigger `codex-daily-usage-record` because they ask for local Codex/ChatGPT usage tracking or daily subscription token records:

- "Can you check token usage from ChatGPT subscription?"
- "Track my Codex token usage every day."
- "Create a daily CSV of Codex tokens from local session logs."
- "Can we aggregate token usage across Hermione and my other machines?"
- "Set up a Hermes cron job that records ChatGPT/Codex usage at night."

These prompts should not trigger it:

- "Review this GitHub PR." (use PR review skills)
- "How many tokens are in this prompt?" (single text tokenization, not Codex subscription logs)
- "Show my OpenAI API billing dashboard." (API billing, not local ChatGPT/Codex subscription logs)
- "Summarize this YouTube transcript." (media synthesis)
- "Send a Discord reminder tomorrow." (scheduled reminder, not token usage recording)

Skill resolver pass condition: realistic usage-tracking prompts route to this skill; unrelated billing, tokenization, PR review, media, and reminder prompts do not.
