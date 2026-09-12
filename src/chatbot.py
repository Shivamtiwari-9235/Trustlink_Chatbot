import os
import re
import sys

from dotenv import load_dotenv

# Load local development settings without overriding cloud environment variables.
load_dotenv()

# Force UTF-8 stream for Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

class TrustLinkGuardrail:
    BANNED_FABRICATIONS = (
        r"bombay\s+native\s+code",
        r"bombay\s+special\s+crimes",
        r"bombay\s+national\s+security",
        r"\bbnsa\b",
        r"delhi\s+police\s+penal\s+code",
    )

    SAFE_FALLBACK = (
        "Is vishay par statutory legal provision hamare verified police database me uplabdh nahi hai. "
        "Kripya aapatkaleen sthiti ya legal sahayata ke liye National Emergency Helpline 112 "
        "ya apne nazdeeki police station sampark karein."
    )

    @staticmethod
    def _format_bullets(text: str) -> str:
        """Remove legacy template fields and keep only useful grounded bullets."""
        ignored_line = re.compile(
            r"(?:not stated|not applicable|none|n/?a|unknown|unmapped|not mentioned|not provided)",
            re.I,
        )
        legacy_key = re.compile(
            r"^(?:offence\s*/\s*topic|new law\s*\([^)]*\)|former law\s*\([^)]*\)|procedure\s*/\s*punishment)\s*:",
            re.I,
        )
        empty_header = re.compile(
            r"^(?:relevant\s+(?:statutory\s+)?section(?:s|\(s\))?|provision\s*/\s*punishment|"
            r"legal\s+(?:right\s*/\s*)?(?:police\s+procedure\s*/\s*)?punishment|"
            r"precaution\s*/\s*next\s*step)\s*:\s*$",
            re.I,
        )
        lines = []
        for line in text.splitlines():
            clean_line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
            if not clean_line or empty_header.match(clean_line) or ignored_line.search(clean_line):
                continue
            clean_line = legacy_key.sub("", clean_line).strip()
            if clean_line:
                lines.append(f"- {clean_line}")
        return "\n".join(lines[:3])

    @classmethod
    def sanitize_output(
        cls,
        text: str,
        allow_devanagari: bool = False,
        fallback: str | None = None,
    ) -> str:
        fallback = fallback or cls.SAFE_FALLBACK
        text = (text or "").strip()
        if len(text) < 10:
            return fallback

        if any(re.search(pattern, text, re.IGNORECASE) for pattern in cls.BANNED_FABRICATIONS):
            return fallback
        if not allow_devanagari and re.search(r"[\u0900-\u097F]", text):
            return fallback

        has_ipc = bool(re.search(r"\b(?:IPC|CrPC|Indian Penal Code|Code of Criminal Procedure)\b", text, re.I))
        has_new_law = bool(
            re.search(
                r"\b(?:BNS|BNSS|MVA|Motor Vehicles Act|IT Act|Information Technology Act)\b",
                text,
                re.I,
            )
        )
        if has_ipc and not has_new_law:
            return fallback
        return text

    @classmethod
    def is_safe_context(cls, context: str) -> bool:
        """Reject a context that could make the model invent a legal source."""
        if not context or any(re.search(pattern, context, re.I) for pattern in cls.BANNED_FABRICATIONS):
            return False
        return bool(
            re.search(
                r"\b(?:BNS|BNSS|MVA|IT Act|FIR|Zero FIR|Bail|112|1930|Article 21)\b",
                context,
                re.I,
            )
        )


class TrustLinkChatbot:
    def __init__(self, model_id=None):
        print("Initializing Knowledge Base...")
        from retriever import LegalRetriever

        self.retriever = LegalRetriever()

        self.model_id = model_id or os.getenv(
            "TRUSTLINK_MODEL_ID", "llama-3.1-8b-instant"
        )
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if self.api_key:
            from groq import Groq

            self.client = Groq(
                api_key=self.api_key,
                timeout=float(os.getenv("GROQ_TIMEOUT_SECONDS", "45")),
                max_retries=0,
            )
        if self.client:
            print(f"Using Groq inference model ({self.model_id})...")
        else:
            print(
                "GROQ_API_KEY is not configured. Add it to the environment "
                "or a local .env file to enable generative answers."
            )
        print("TrustLink AI Assistant Ready with Hard Guardrails!\n")

    @staticmethod
    def _configuration_message() -> str:
        return (
            "TrustLink is ready, but generative answers are not configured. "
            "Set GROQ_API_KEY in the Streamlit deployment secrets or in a local .env file, "
            "then restart the app."
        )

    @staticmethod
    def _query_language(user_query: str) -> str:
        if re.search(r"[\u0900-\u097F]", user_query):
            return "hindi"
        if re.search(
            r"\b(?:kya|kaise|kahan|kaun|kagaz|dastavez|gaadi|gadi|chalate|chala|rakhen|rakhna|hai|hain|par|ke|ki|ko)\b",
            user_query.lower(),
        ):
            return "hinglish"
        return "english"

    @classmethod
    def _is_hindi_query(cls, user_query: str) -> bool:
        return cls._query_language(user_query) == "hindi"

    @staticmethod
    def _fallback_for_language(language: str) -> str:
        if language == "english":
            return (
                "This topic is not available in the verified police database. "
                "For emergencies or legal assistance, call 112 or contact a nearby police station."
            )
        if language == "hinglish":
            return (
                "Is topic par verified police database me information available nahi hai. "
                "Emergency ya legal help ke liye 112 call karein ya nearest police station se contact karein."
            )
        return (
            "Is topic par verified police database me information available nahi hai. "
            "Emergency ya legal help ke liye 112 call karein ya nearest police station se contact karein."
        )

    @staticmethod
    def _has_devanagari(text: str) -> bool:
        return bool(re.search(r"[\u0900-\u097F]", text))

    @staticmethod
    def _has_complete_sentences(text: str) -> bool:
        text = (text or "").strip()
        return bool(text) and bool(re.search(r"[.!?।][\"')\]]*$", text))

    @classmethod
    def _matches_query_language(cls, text: str, language: str) -> bool:
        has_devanagari = cls._has_devanagari(text)
        return not has_devanagari

    @staticmethod
    def _document_requirement_answer(user_query: str) -> str | None:
        if not re.search(
            r"(?:document|documents|paper|papers|kagaz|dastavez|license|licence|rc|puc)",
            user_query,
            re.IGNORECASE,
        ) or not re.search(
            r"(?:drive|driving|vehicle|car|bike|gaadi|gadi|chal)",
            user_query,
            re.IGNORECASE,
        ):
            return None

        if TrustLinkChatbot._query_language(user_query) in ("hindi", "hinglish"):
            return (
                "- Relevant statutory section(s): Motor Vehicles Act\n"
                "- Legal requirement: Valid Driving Licence, Registration Certificate (RC), motor insurance aur valid PUC Certificate rakhein.\n"
                "- Next step: Original documents ya verifiable electronic versions DigiLocker/mParivahan me dikhayein; current State/RTO rules check karein."
            )
        return (
            "- Relevant statutory section(s): Motor Vehicles Act\n"
            "- Legal requirement: Carry a valid Driving Licence, Registration Certificate (RC), motor insurance and valid PUC Certificate.\n"
            "- Next step: Show original or verifiable electronic documents in DigiLocker/mParivahan and check current State/RTO rules."
        )

    @staticmethod
    def _verified_extraction(chunk: str, language: str) -> str:
        """Build optional bullets from trusted context without inventing missing mappings."""
        chunk = re.sub(r"^Statutory metadata:\s*[^.]+\.\s*", "", chunk, count=1, flags=re.I)
        title, _, details = chunk.partition(":")
        section = re.search(
            r"Section[s]?\s+[\d(), &]+\s+(?:BNS|BNSS|MVA|IT Act)", chunk, re.I
        )
        clean_details = details.strip()
        if clean_details.lower().startswith(title.lower()):
            clean_details = clean_details[len(title):].lstrip(" :-")
        if language == "english":
            clean_details = re.sub(r"\b(ko|ke|ki|me|par|hai|hain|se|ka|karein|rakhen)\b", "", clean_details, flags=re.I)
        section_text = section.group(0) if section else title.strip()
        return (
            f"- Relevant statutory section(s): {section_text}.\n"
            f"- Legal right / police procedure / punishment: {clean_details.rstrip('.')} ."
        )

    def generate_response(self, user_query: str) -> str:
        language = self._query_language(user_query)
        fallback = self._fallback_for_language(language)
        document_answer = self._document_requirement_answer(user_query)
        if document_answer:
            return document_answer

        matched_results = self.retriever.retrieve(user_query, top_k=4, threshold=0.28)

        if not matched_results:
            return fallback

        context_text = "\n\n".join(chunk for chunk, _ in matched_results)
        if not TrustLinkGuardrail.is_safe_context(context_text):
            return fallback

        language_instruction = (
            "Reply in clear, natural Hinglish using only the Latin alphabet because the citizen asked in Hindi."
            if language == "hindi"
            else "Reply in clean, natural Hinglish using only the Latin alphabet because the citizen asked in Hinglish."
            if language == "hinglish"
            else "Reply entirely in professional, grammatically correct English because the citizen asked in English."
        )
        system_instruction = (
            "You are TrustLink, an official Indian Police Legal AI Assistant.\n"
            "STRICT RULES:\n"
            "1. Extraction first: select only facts and section numbers explicitly present in the Verified Legal Context. Never guess, merge, or add a section.\n"
            "2. Language: Mirror the user's language strictly (English query -> professional English, Hindi/Hinglish query -> clear Hinglish).\n"
            "3. Completeness: Always generate complete sentences. Never cut off mid-thought or mid-sentence.\n"
            "4. Output Structure: Use clean bullet points only when relevant facts are present:\n"
            "- Relevant Section(s): [New Law & Former Law, when present]\n"
            "- Legal Provision & Penalty: [Clear, complete statutory explanation from context]\n"
            "- Police Procedure / Citizen Rights: [Actionable procedure, only when supported by context]\n"
            "Never output empty headers or placeholder lines.\n"
            "5. Omit any unsupported category completely. Never write 'Not stated', 'None', 'Not applicable', or raw key-value template fields.\n"
            "6. Answer the citizen's actual question directly. Do not force a traffic, arrest, offence, or punishment answer when the question asks about documents, procedure, rights, or prevention.\n"
            "7. " + language_instruction + " Do not mix languages or scripts.\n"
            "8. End every bullet with a complete sentence and stop after the supported answer."
        )

        user_content = (
            f"--- VERIFIED LEGAL CONTEXT ---\n"
            f"{context_text}\n"
            f"--- END CONTEXT ---\n\n"
            f"Citizen Query: {user_query}\n\n"
            f"Legal Answer:"
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content},
        ]

        if self.client is None:
            return self._configuration_message()

        try:
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=0.1,
                max_tokens=180,
            )
            raw_output = (completion.choices[0].message.content or "").strip()
        except Exception as error:
            print(f"Groq inference failed: {error}")
            raw_output = ""

        formatted_output = TrustLinkGuardrail._format_bullets(raw_output)
        checked_output = TrustLinkGuardrail.sanitize_output(
            formatted_output,
            allow_devanagari=False,
            fallback=fallback,
        )
        if (
            checked_output != fallback
            and self._matches_query_language(checked_output, language)
            and self._has_complete_sentences(checked_output)
        ):
            return checked_output

        verified_output = self._verified_extraction(matched_results[0][0], language)
        verified_output = TrustLinkGuardrail._format_bullets(verified_output)
        verified_checked = TrustLinkGuardrail.sanitize_output(
            verified_output,
            allow_devanagari=False,
            fallback=fallback,
        )
        return (
            verified_checked
            if verified_checked != fallback
            and self._matches_query_language(verified_checked, language)
            else fallback
        )


def run_cli():
    bot = TrustLinkChatbot()
    print("=== TrustLink Police Assistance Terminal (Guardrails Active) ===")
    print("Type 'exit' or 'quit' to terminate.\n")

    while True:
        try:
            query = input("\nCitizen: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit"]:
                print("Session closed. Stay safe!")
                break

            response = bot.generate_response(query)
            print(f"\nTrustLink:\n{response}")
        except (KeyboardInterrupt, EOFError):
            print("\nSession closed. Stay safe!")
            break


if __name__ == "__main__":
    run_cli()