import os
from typing import List, Dict, Any, Union


# ─────────────────────────────────────────────────────────────────────────────
#  COO Prompt Builder
#  Accepts either raw processor events (dicts) or BusinessEvent objects.
#  The output asks the LLM to act as a startup COO — not a summariser.
# ─────────────────────────────────────────────────────────────────────────────
def _build_prompt(events: List[Any], is_daily: bool, preferences: str, source_errors: List[str] = None) -> str:
    if is_daily:
        intro = (
            "You are the Founder's Chief of Staff.\n"
            "Generate a 'BIG PICTURE' Daily Executive Brief for today.\n"
            f"Founder preferences: {preferences}\n\n"
            "Structure your response exactly like this:\n"
            "📅 YESTERDAY IN ONE LINE: <single sentence summary>\n\n"
            "🏆 TOP WIN: <best thing that happened>\n\n"
            "🔴 UNRESOLVED RISKS: <bullet list — anything still open>\n\n"
            "🎯 TODAY'S PRIORITY: <the ONE most important thing for the founder>\n\n"
            "Digest history from past 24 hours:\n\n"
        )
    else:
        intro = (
            "You are a startup COO acting as the founder's AI decision assistant.\n"
            f"Founder preferences: {preferences}\n\n"
            "Your ONLY job is to convert operational signals into a clear decision brief.\n"
            "Be direct, human, and specific. No jargon. No fluff.\n"
            "Imagine you are briefing the founder in a 60-second standup.\n\n"
            "Format your response EXACTLY like this (use the emojis):\n\n"
            "🔴 ACTION REQUIRED:\n"
            "  1. [specific action with client/task name]\n"
            "  (list only actions that need attention in the next 2 hours)\n\n"
            "🟡 FOR AWARENESS:\n"
            "  • [things that need attention today but not immediately]\n\n"
            "✅ ALL CLEAR:\n"
            "  • [what is working fine — keep it brief]\n\n"
            "📌 BOTTOM LINE: [ONE sentence — what the founder should focus on right now]\n"
        )
        if source_errors:
            intro += "\n⚠️ SOURCE ISSUES (some data may be missing):\n"
            for err in source_errors:
                intro += f"  • {err}\n"
        intro += "\nOperational signals:\n\n"

    # Render events — support both BusinessEvent objects and plain dicts
    for event in events:
        if hasattr(event, "to_prompt_line"):
            # BusinessEvent from intelligence layer
            prompt_line = event.to_prompt_line()
        elif isinstance(event, dict):
            age    = f" [{event.get('age_hours', 0):.1f}h old]" if event.get("age_hours") else ""
            action = f" → {event.get('suggested_action', '')}" if event.get("suggested_action") else ""
            sev    = event.get("severity", "INFO")
            src    = event.get("source", "unknown")
            con    = event.get("content", "")
            prompt_line = f"[{sev}] {src}{age}: {con}{action}"
        else:
            prompt_line = str(event)
        intro += f"• {prompt_line}\n"

    return intro




class Summarizer:
    """
    Multi-provider AI summariser.

    Provider priority (first available key wins):
        1. Google Gemini   (GEMINI_API_KEY)     – free tier, default
        2. Anthropic Claude (ANTHROPIC_API_KEY) – paid, high quality
        3. OpenAI           (OPENAI_API_KEY)    – paid, widely used

    The active provider can be forced via settings.yaml  →  ai.provider: gemini | anthropic | openai
    Falls back to a rich mock digest when no key is available.
    """

    def __init__(self, gemini_key: str = None, anthropic_key: str = None,
                 openai_key: str = None, provider: str = "auto"):
        # Project root is two levels up from this file
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.feedback_path = os.path.join(PROJECT_ROOT, "heartbeat_app", "config", "feedback.txt")
        self.provider = provider.lower()  # "auto" | "gemini" | "anthropic" | "openai"

        # Normalise – treat placeholder strings as absent
        self._gemini_key    = gemini_key    if gemini_key    and "your-key" not in gemini_key    else None
        self._anthropic_key = anthropic_key if anthropic_key and "your-key" not in anthropic_key else None
        self._openai_key    = openai_key    if openai_key    and "your-key" not in openai_key    else None

    # ── helpers ──────────────────────────────────────────────────────────────
    def _get_founder_preferences(self) -> str:
        if os.path.exists(self.feedback_path):
            try:
                with open(self.feedback_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return "Keep it short, professional, and action-focused."

    def _provider_order(self) -> List[str]:
        """Return providers in the order they should be tried."""
        if self.provider == "auto":
            return ["gemini", "anthropic", "openai"]
        # User forced a specific provider → try that first, then fallbacks
        order = [self.provider]
        for p in ["gemini", "anthropic", "openai"]:
            if p not in order:
                order.append(p)
        return order

    # ── per-provider callers ──────────────────────────────────────────────────
    def _call_gemini(self, prompt: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self._gemini_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self._anthropic_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _call_openai(self, prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self._openai_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    # ── key lookup ───────────────────────────────────────────────────────────
    def _key_for(self, provider: str):
        return {"gemini": self._gemini_key,
                "anthropic": self._anthropic_key,
                "openai": self._openai_key}.get(provider)

    def _call_provider(self, provider: str, prompt: str) -> str:
        callers = {
            "gemini":    self._call_gemini,
            "anthropic": self._call_anthropic,
            "openai":    self._call_openai,
        }
        return callers[provider](prompt)

    # ── public API ────────────────────────────────────────────────────────────
    def summarize(self, events: List[Dict[str, Any]], is_daily: bool = False, source_errors: List[str] = None) -> str:
        """Generate a digest using the best available AI provider."""
        if not events and not is_daily:
            # Check for source errors even in "All Smooth" case
            if source_errors:
                return f"🟢 All systems running smoothly, but {len(source_errors)} sources failed. Check log."
            return "🟢 All systems running smoothly. No new updates."

        pref   = self._get_founder_preferences()
        prompt = _build_prompt(events, is_daily, pref, source_errors)

        for provider in self._provider_order():
            if not self._key_for(provider):
                continue
            try:
                print(f"🧠 Generating {'DAILY' if is_daily else 'QUICK'} digest with {provider.upper()}...")
                result = self._call_provider(provider, prompt)
                print(f"✅ Digest generated by {provider.upper()}.")
                return result
            except ImportError:
                print(f"⚠️  '{provider}' library not installed. Trying next provider...")
            except Exception as e:
                print(f"⚠️  {provider.upper()} error: {e}. Trying next provider...")

        # ── Rich mock fallback ────────────────────────────────────────────────
        print("ℹ️  No AI keys configured. Using MOCK digest.")
        if is_daily:
            return (
                "📅 **DAILY EXECUTIVE SUMMARY (MOCK)**\n"
                "🟢 System Status: All services operational. 3 connectors active.\n"
                "🔴 Critical Items:\n"
                "   • Client ABC waiting for reply since 12 hrs\n"
                "   • 1 GitHub PR stale for 2 days\n"
                "📌 Recommended Actions:\n"
                "   1. Reply to Client ABC on Slack\n"
                "   2. Review & merge stale PR #42\n"
                "⏱️ Next Check-in: Evening standup"
            )

        mock_error_tag = f"\n⚠️ SOURCE ISSUES: {source_errors[0]}" if source_errors else ""
        return (
            "🔴 **ACTION REQUIRED:**\n"
            "   1. Respond to client deadline message within 2 hours\n"
            "   2. Assign Q2 Roadmap task to team lead\n\n"
            "🟡 **FOR AWARENESS:**\n"
            "   • Client: Project deadline concern (Slack — 3h ago)\n"
            "   • Overdue Notion task: Q2 Roadmap review\n\n"
            "✅ **ALL CLEAR:**\n"
            "   • System infrastructure 100% UP\n\n"
            "📌 **BOTTOM LINE:** Focused attention on Client XYZ and today's roadmap deliverables."
            f"{mock_error_tag}"
        )
