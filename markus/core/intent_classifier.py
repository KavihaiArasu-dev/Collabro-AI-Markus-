"""
Markus AI — Intent Classifier (§4, new)

Classifies user input into intent categories:
CHAT, CODE, DEBUG, SYSTEM_CONTROL, RESEARCH, AUTOMATION, etc.

Uses keyword heuristics for instant classification and can optionally
escalate to an LLM (via /fast route) for ambiguous inputs.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from config.constants import IntentType

logger = logging.getLogger(__name__)


# Keyword patterns for each intent type
INTENT_PATTERNS: dict[IntentType, list[str]] = {
    IntentType.CODE: [
        r"\b(write|create|implement|code|function|class|method|refactor|optimize)\b",
        r"\b(python|javascript|typescript|react|html|css|java|rust|go|sql)\b",
        r"\b(api|endpoint|route|component|module|package)\b",
        r"\b(algorithm|data structure|sort|search|parse)\b",
    ],
    IntentType.DEBUG: [
        r"\b(debug|fix|error|bug|issue|crash|exception|traceback|stack trace)\b",
        r"\b(broken|failing|doesn't work|not working|wrong output)\b",
        r"\b(memory leak|performance issue|slow|timeout)\b",
    ],
    IntentType.SYSTEM_CONTROL: [
        r"\b(open|launch|start|close|kill|stop|restart)\b.*\b(app|application|program|process)\b",
        r"\b(run|execute)\b.*\b(command|script|terminal|shell)\b",
        r"\b(file|folder|directory)\b.*\b(create|delete|move|copy|rename)\b",
        r"\b(system|cpu|ram|memory|disk|gpu|battery|network)\b.*\b(status|info|check|monitor)\b",
    ],
    IntentType.RESEARCH: [
        r"\b(research|find|search|look up|what is|explain|how does|documentation)\b",
        r"\b(compare|difference between|pros and cons|best practice)\b",
        r"\b(library|framework|tool|package|dependency)\b.*\b(find|recommend|suggest)\b",
    ],
    IntentType.AUTOMATION: [
        r"\b(automate|schedule|cron|repeat|batch|pipeline|workflow)\b",
        r"\b(ci|cd|deploy|build|test)\b.*\b(automat|run|trigger)\b",
    ],
    IntentType.REVIEW: [
        r"\b(review|check|audit|inspect|analyze)\b.*\b(code|security|performance)\b",
        r"\b(code review|pull request|pr|merge request)\b",
    ],
    IntentType.ARCHITECTURE: [
        r"\b(architect|design|structure|organize|plan)\b.*\b(project|system|app|database|api)\b",
        r"\b(folder structure|project setup|database schema|api design)\b",
    ],
    IntentType.DOCUMENTATION: [
        r"\b(document|readme|docs|api doc|guide|tutorial)\b",
        r"\b(write|generate|create)\b.*\b(documentation|readme|guide)\b",
    ],
    IntentType.MEMORY: [
        r"\b(remember|recall|forget|memory)\b",
        r"\b(what did|last time|previous|history)\b",
    ],
    IntentType.RAG: [
        r"\b(knowledge base|search docs|find in|look in)\b",
        r"\b(upload|ingest|index)\b.*\b(document|file|pdf|markdown)\b",
    ],
    IntentType.QUESTION: [
        r"\b(who|what|where|when|why|how|which|can you|is it|does it)\b",
        r"\b(tell me|explain to me|help me understand)\b",
    ],
    IntentType.SEARCH: [
        r"\b(search for|google|look up on the web|find online)\b",
        r"\b(web search|browse for|query)\b",
    ],
    IntentType.FILE_OPERATION: [
        r"\b(file|folder|directory)\b.*\b(create|delete|move|copy|rename|search|find|read|write)\b",
        r"\b(read file|write to file|save file|list directory|find file)\b",
    ],
    IntentType.APP_CONTROL: [
        r"\b(open|launch|start|close|terminate|kill|restart)\b.*\b(app|application|program|software|chrome|vscode|spotify)\b",
    ],
    IntentType.BROWSER_AUTOMATION: [
        r"\b(open website|open url|go to website|navigate to|search web|open in browser)\b",
    ],
    IntentType.TASK_MANAGEMENT: [
        r"\b(task|todo|to-do|project tasks|assign task|create task|track task)\b",
    ],
    IntentType.MULTI_STEP_ACTION: [
        r"\b(first|then|after that|finally|steps|step 1|multi-step|workflow)\b",
    ],
    IntentType.SETTINGS: [
        r"\b(settings|preferences|configure|config|setup)\b",
        r"\b(change|update|modify)\b.*\b(setting|preference|theme|model)\b",
    ],
}

# ── Pre-compile all regex patterns at module load (avoid recompiling on every classify call) ──
_COMPILED_INTENT_PATTERNS: dict[IntentType, list[re.Pattern]] = {
    intent: [re.compile(pattern) for pattern in patterns]
    for intent, patterns in INTENT_PATTERNS.items()
}


class IntentClassifier:
    """
    Classifies user input into intent types.

    Uses a two-stage approach:
    1. Fast keyword/pattern matching (deterministic, no LLM needed)
    2. Optional LLM-based classification for ambiguous inputs (via /fast route)
    """

    def classify(self, user_input: str) -> IntentType:
        """
        Classify user input into an intent type.

        Returns the most likely intent based on keyword pattern matching.
        Falls back to CHAT for unrecognized inputs.
        """
        if not user_input or not user_input.strip():
            return IntentType.CHAT

        input_lower = user_input.lower()
        scores: dict[IntentType, int] = {}

        for intent, compiled_patterns in _COMPILED_INTENT_PATTERNS.items():
            score = 0
            for pattern in compiled_patterns:
                matches = pattern.findall(input_lower)
                score += len(matches)
            if score > 0:
                scores[intent] = score

        if not scores:
            return IntentType.CHAT

        # Return the highest-scoring intent
        best_intent = max(scores, key=lambda k: scores[k])
        logger.debug(f"Intent classified: {best_intent.value} (score={scores[best_intent]}) for: {user_input[:80]}...")
        return best_intent

    def classify_with_confidence(self, user_input: str) -> tuple[IntentType, float]:
        """
        Classify with a confidence score (0.0 to 1.0).
        If confidence is low, the caller may want to use LLM-based classification.
        """
        if not user_input or not user_input.strip():
            return IntentType.CHAT, 1.0

        input_lower = user_input.lower()
        scores: dict[IntentType, int] = {}

        for intent, compiled_patterns in _COMPILED_INTENT_PATTERNS.items():
            score = 0
            for pattern in compiled_patterns:
                matches = pattern.findall(input_lower)
                score += len(matches)
            if score > 0:
                scores[intent] = score

        if not scores:
            return IntentType.CHAT, 0.5  # Default with moderate confidence

        total = sum(scores.values())
        best_intent = max(scores, key=lambda k: scores[k])
        confidence = scores[best_intent] / total if total > 0 else 0.5

        return best_intent, min(confidence, 1.0)

    def analyze_category(self, user_input: str) -> tuple[str, IntentType]:
        """
        Analyze whether the input is a 'question' (to be answered directly)
        or a 'task' (to be executed via code/tools/agents).
        
        Returns:
            tuple of (category: 'question' | 'task' | 'chat', intent: IntentType)
        """
        if not user_input or not user_input.strip():
            return "chat", IntentType.CHAT

        input_lower = user_input.lower().strip()
        intent = self.classify(user_input)

        # Question signals: starts with question words or asks for explanations/info
        question_starters = (
            "what", "how", "why", "who", "when", "where", "which", "whose", "whom",
            "can you explain", "could you explain", "explain", "tell me about",
            "tell me", "is it", "is there", "are there", "does", "do", "did",
            "what's", "whats", "how's", "hows", "why's", "whys", "help me understand"
        )
        
        # Explicit task signals: imperative verbs asking to perform an action
        task_starters = (
            "write", "create", "build", "generate", "code", "implement", "make",
            "fix", "debug", "refactor", "optimize", "delete", "remove", "clean",
            "run", "execute", "start", "launch", "open", "close", "kill", "restart",
            "automate", "schedule", "deploy", "install", "test", "compile"
        )

        if any(input_lower.startswith(w) for w in question_starters) or "?" in user_input:
            # If it's asking a question, even if it mentions code (e.g. "what is Python?"), it's a question
            if not any(input_lower.startswith(w) for w in task_starters):
                return "question", intent if intent in (IntentType.QUESTION, IntentType.RESEARCH, IntentType.DOCUMENTATION) else IntentType.QUESTION

        if any(input_lower.startswith(w) for w in task_starters) or intent in (
            IntentType.CODE, IntentType.DEBUG, IntentType.SYSTEM_CONTROL,
            IntentType.AUTOMATION, IntentType.FILE_OPERATION, IntentType.APP_CONTROL,
            IntentType.BROWSER_AUTOMATION, IntentType.MULTI_STEP_ACTION
        ):
            return "task", intent

        if intent in (IntentType.QUESTION, IntentType.RESEARCH):
            return "question", intent

        return "chat", intent


# Singleton
intent_classifier = IntentClassifier()

