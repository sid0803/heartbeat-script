import os
import time
from typing import List, Dict, Any, Union

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
            "Be direct, human, and specific. No jargon. No fluff.\n\n"
            "Format your response EXACTLY like this (use the emojis):\n\n"
            "🔴 ACTION REQUIRED:\n"
            "  1. [specific action with client/task name]\n\n"
            "🟡 FOR AWARENESS:\n"
            "  • [things that need attention today but not immediately]\n\n"
            "✅ ALL CLEAR:\n"
            "  • [what is working fine — keep it brief]\n\n"
            "📌 BOTTOM LINE: [ONE sentence]\n"
        )
        if source_errors:
            intro += "\n⚠️ SOURCE ISSUES (some data may be missing):\n"
            for err in source_errors: intro += f"  • {err}\n"
        intro += "\nOperational signals:\n\n"

    for event in events:
        if hasattr(event, "to_prompt_line"): prompt_line = event.to_prompt_line()
        elif isinstance(event, dict):
            age = f" [{event.get('age_hours', 0):.1f}h old]" if event.get("age_hours") else ""
            prompt_line = f"[{event.get('severity', 'INFO')}] {event.get('source', 'unknown')}{age}: {event.get('content', '')}"
        else: prompt_line = str(event)
        intro += f"• {prompt_line}\n"
    return intro

class Summarizer:
    def __init__(self, gemini_key: str = None, anthropic_key: str = None, openai_key: str = None, provider: str = "auto"):
        PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
        self.feedback_path = os.path.join(PROJECT_ROOT, "heartbeat_app", "config", "feedback.txt")
        self.provider = provider.lower()
        self._gemini_key    = gemini_key    if gemini_key    and "your-key" not in gemini_key    else None
        self._anthropic_key = anthropic_key if anthropic_key and "your-key" not in anthropic_key else None
        self._openai_key    = openai_key    if openai_key    and "your-key" not in openai_key    else None

    def _get_founder_preferences(self) -> str:
        if os.path.exists(self.feedback_path):
            try:
                with open(self.feedback_path, "r", encoding="utf-8") as f: return f.read().strip()
            except: pass
        return "Keep it short, professional, and action-focused."

    def _provider_order(self) -> List[str]:
        if self.provider == "auto": return ["gemini", "anthropic", "openai"]
        order = [self.provider]
        for p in ["gemini", "anthropic", "openai"]:
            if p not in order: order.append(p)
        return order

    def _call_gemini(self, prompt: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self._gemini_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model.generate_content(prompt).text

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self._anthropic_key)
        return client.messages.create(model="claude-3-haiku-20240307", max_tokens=600, messages=[{"role": "user", "content": prompt}]).content[0].text

    def _call_openai(self, prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self._openai_key)
        return client.chat.completions.create(model="gpt-4o-mini", max_tokens=600, messages=[{"role": "user", "content": prompt}]).choices[0].message.content

    def _key_for(self, provider: str):
        return {"gemini": self._gemini_key, "anthropic": self._anthropic_key, "openai": self._openai_key}.get(provider)

    def _call_provider(self, provider: str, prompt: str) -> str:
        callers = {"gemini": self._call_gemini, "anthropic": self._call_anthropic, "openai": self._call_openai}
        return callers[provider](prompt)

    def summarize(self, events: List[Dict[str, Any]], is_daily: bool = False, source_errors: List[str] = None) -> str:
        if not events and not is_daily:
            if source_errors: return f"🟢 All clear, but {len(source_errors)} sources failed."
            return "🟢 All clear. No new updates."
        pref   = self._get_founder_preferences()
        prompt = _build_prompt(events, is_daily, pref, source_errors)
        for provider in self._provider_order():
            if not self._key_for(provider): continue
            try:
                print(f"🧠 Generating digest with {provider.upper()}...")
                return self._call_provider(provider, prompt)
            except Exception as e: print(f"⚠️  {provider.upper()} error: {e}")
        
        print("ℹ️  Using MOCK digest fallback.")
        mock_error_tag = f"\n⚠️ SOURCE ISSUES: {source_errors[0]}" if source_errors else ""
        return "🔴 ACTION REQUIRED:\n   1. Reply to client deadline message within 2 hours\n\n🟡 FOR AWARENESS:\n   • Project deadline concern (Slack — 3h ago)\n\n✅ ALL CLEAR:\n   • System infrastructure UP\n\n📌 BOTTOM LINE: Focus on Client XYZ." + mock_error_tag
