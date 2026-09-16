/**
 * Markus AI — Intent Classifier (§4)
 *
 * Classifies user input into intent categories using keyword/regex heuristics.
 * Direct port from core/intent_classifier.py — preserving all patterns exactly.
 */

import { IntentType } from "@/lib/config/constants";

// Keyword patterns for each intent type
const INTENT_PATTERNS: Record<IntentType, RegExp[]> = {
  [IntentType.CODE]: [
    /\b(write|create|implement|code|function|class|method|refactor|optimize)\b/,
    /\b(python|javascript|typescript|react|html|css|java|rust|go|sql)\b/,
    /\b(api|endpoint|route|component|module|package)\b/,
    /\b(algorithm|data structure|sort|search|parse)\b/,
  ],
  [IntentType.DEBUG]: [
    /\b(debug|fix|error|bug|issue|crash|exception|traceback|stack trace)\b/,
    /\b(broken|failing|doesn't work|not working|wrong output)\b/,
    /\b(memory leak|performance issue|slow|timeout)\b/,
  ],
  [IntentType.SYSTEM_CONTROL]: [
    /\b(open|launch|start|close|kill|stop|restart)\b.*\b(app|application|program|process)\b/,
    /\b(run|execute)\b.*\b(command|script|terminal|shell)\b/,
    /\b(file|folder|directory)\b.*\b(create|delete|move|copy|rename)\b/,
    /\b(system|cpu|ram|memory|disk|gpu|battery|network)\b.*\b(status|info|check|monitor)\b/,
    /\b(volume|mute|unmute|louder|quieter|softer)\b/,
    /\b(brightness|brighter|dimmer|darker)\b/,
    /\b(screenshot|screen capture|screen grab|capture screen)\b/,
    /\b(lock screen|shutdown|shut down|restart|reboot|power off)\b/,
    /\b(battery level|battery status|how much battery)\b/,
    /\b(network status|internet status|am i connected)\b/,
    /\b(uptime|system uptime)\b/,
    /\b(wifi|wi-fi|wireless)\b/,
  ],
  [IntentType.RESEARCH]: [
    /\b(research|find|search|look up|what is|explain|how does|documentation)\b/,
    /\b(compare|difference between|pros and cons|best practice)\b/,
    /\b(library|framework|tool|package|dependency)\b.*\b(find|recommend|suggest)\b/,
  ],
  [IntentType.AUTOMATION]: [
    /\b(automate|schedule|cron|repeat|batch|pipeline|workflow)\b/,
    /\b(ci|cd|deploy|build|test)\b.*\b(automat|run|trigger)\b/,
  ],
  [IntentType.REVIEW]: [
    /\b(review|check|audit|inspect|analyze)\b.*\b(code|security|performance)\b/,
    /\b(code review|pull request|pr|merge request)\b/,
  ],
  [IntentType.ARCHITECTURE]: [
    /\b(architect|design|structure|organize|plan)\b.*\b(project|system|app|database|api)\b/,
    /\b(folder structure|project setup|database schema|api design)\b/,
  ],
  [IntentType.DOCUMENTATION]: [
    /\b(document|readme|docs|api doc|guide|tutorial)\b/,
    /\b(write|generate|create)\b.*\b(documentation|readme|guide)\b/,
  ],
  [IntentType.MEMORY]: [
    /\b(remember|recall|forget|memory)\b/,
    /\b(what did|last time|previous|history)\b/,
  ],
  [IntentType.RAG]: [
    /\b(knowledge base|search docs|find in|look in)\b/,
    /\b(upload|ingest|index)\b.*\b(document|file|pdf|markdown)\b/,
  ],
  [IntentType.QUESTION]: [
    /\b(who|what|where|when|why|how|which|can you|is it|does it)\b/,
    /\b(tell me|explain to me|help me understand)\b/,
  ],
  [IntentType.SEARCH]: [
    /\b(search for|google|look up on the web|find online)\b/,
    /\b(web search|browse for|query)\b/,
    /\b(search the web|search online|search internet)\b/,
    /\b(news about|latest news|what's the news)\b/,
  ],
  [IntentType.FILE_OPERATION]: [
    /\b(file|folder|directory)\b.*\b(create|delete|move|copy|rename|search|find|read|write)\b/,
    /\b(read file|write to file|save file|list directory|find file)\b/,
  ],
  [IntentType.APP_CONTROL]: [
    /\b(open|launch|start|close|terminate|kill|restart)\b.*\b(app|application|program|software)\b/,
    /\b(open|launch|start|close|terminate|kill)\s+(chrome|firefox|edge|brave|safari|opera)\b/,
    /\b(open|launch|start|close|terminate|kill)\s+(whatsapp|telegram|discord|slack|zoom|teams|skype|signal)\b/,
    /\b(open|launch|start|close|terminate|kill)\s+(spotify|vlc|netflix|itunes)\b/,
    /\b(open|launch|start|close|terminate|kill)\s+(vscode|vs code|visual studio|sublime|notepad|terminal|cmd|powershell)\b/,
    /\b(open|launch|start|close|terminate|kill)\s+(word|excel|powerpoint|outlook)\b/,
    /\b(open|launch|start|close|terminate|kill)\s+(explorer|finder|file explorer|task manager|calculator|paint|settings|camera|store)\b/,
    /\b(list|show|what are)\s+(running|active)\s+(apps|applications|programs|processes)\b/,
  ],
  [IntentType.BROWSER_AUTOMATION]: [
    /\b(open website|open url|go to website|navigate to|search web|open in browser)\b/,
    /\b(open|go to|visit|navigate to)\s+\S+\.(com|org|net|io|dev|ai|co)\b/,
  ],
  [IntentType.YOUTUBE]: [
    /\b(play|play me)\b.*\b(on youtube|youtube|on yt)\b/,
    /\b(youtube|yt)\s+(play|search|find)\b/,
    /\b(play)\s+.+\s+(song|music|video|track)\b/,
    /\b(search youtube|youtube search|search on youtube)\b/,
  ],
  [IntentType.TASK_MANAGEMENT]: [
    /\b(task|todo|to-do|project tasks|assign task|create task|track task)\b/,
  ],
  [IntentType.MULTI_STEP_ACTION]: [
    /\b(first|then|after that|finally|steps|step 1|multi-step|workflow)\b/,
  ],
  [IntentType.SETTINGS]: [
    /\b(settings|preferences|configure|config|setup)\b/,
    /\b(change|update|modify)\b.*\b(setting|preference|theme|model)\b/,
  ],
  [IntentType.CHAT]: [],
  [IntentType.VOICE_COMMAND]: [],
};

class IntentClassifier {
  /**
   * Classify user input into an intent type.
   * Uses keyword pattern matching. Falls back to CHAT for unrecognized inputs.
   */
  classify(userInput: string): IntentType {
    if (!userInput || !userInput.trim()) {
      return IntentType.CHAT;
    }

    const inputLower = userInput.toLowerCase();
    const scores: Partial<Record<IntentType, number>> = {};

    for (const [intent, patterns] of Object.entries(INTENT_PATTERNS)) {
      let score = 0;
      for (const pattern of patterns) {
        const matches = inputLower.match(pattern);
        if (matches) {
          score += matches.length;
        }
      }
      if (score > 0) {
        scores[intent as IntentType] = score;
      }
    }

    const entries = Object.entries(scores) as [IntentType, number][];
    if (entries.length === 0) {
      return IntentType.CHAT;
    }

    // Return the highest-scoring intent
    entries.sort((a, b) => b[1] - a[1]);
    return entries[0][0];
  }

  /**
   * Classify with a confidence score (0.0 to 1.0).
   */
  classifyWithConfidence(userInput: string): [IntentType, number] {
    if (!userInput || !userInput.trim()) {
      return [IntentType.CHAT, 1.0];
    }

    const inputLower = userInput.toLowerCase();
    const scores: Partial<Record<IntentType, number>> = {};

    for (const [intent, patterns] of Object.entries(INTENT_PATTERNS)) {
      let score = 0;
      for (const pattern of patterns) {
        const matches = inputLower.match(pattern);
        if (matches) {
          score += matches.length;
        }
      }
      if (score > 0) {
        scores[intent as IntentType] = score;
      }
    }

    const entries = Object.entries(scores) as [IntentType, number][];
    if (entries.length === 0) {
      return [IntentType.CHAT, 0.5];
    }

    const total = entries.reduce((sum, [, s]) => sum + s, 0);
    entries.sort((a, b) => b[1] - a[1]);
    const bestIntent = entries[0][0];
    const confidence = total > 0 ? Math.min(entries[0][1] / total, 1.0) : 0.5;

    return [bestIntent, confidence];
  }

  /**
   * Analyze whether the input is a 'question' (to be answered directly)
   * or a 'task' (to be executed via code/tools/agents).
   */
  analyzeCategory(userInput: string): [string, IntentType] {
    if (!userInput || !userInput.trim()) {
      return ["chat", IntentType.CHAT];
    }

    const inputLower = userInput.toLowerCase().trim();
    const intent = this.classify(userInput);

    const questionStarters = [
      "what", "how", "why", "who", "when", "where", "which", "whose", "whom",
      "can you explain", "could you explain", "explain", "tell me about",
      "tell me", "is it", "is there", "are there", "does", "do", "did",
      "what's", "whats", "how's", "hows", "why's", "whys", "help me understand",
      "என்ன", "எப்படி", "யார்", "ஏன்", "எங்கே", "எப்போது", "எது",
    ];

    const taskStarters = [
      "write", "create", "build", "generate", "code", "implement", "make",
      "fix", "debug", "refactor", "optimize", "delete", "remove", "clean",
      "run", "execute", "start", "launch", "open", "close", "kill", "restart",
      "automate", "schedule", "deploy", "install", "test", "compile",
      "play", "search", "mute", "unmute", "screenshot", "lock", "shutdown",
      "volume", "brightness", "focus", "switch",
      "திற", "திறக்க", "மூடு", "மூடவும்", "எடு", "போடு", "இயக்கு", "குறை", "கூட்டு",
      "அதிகரி", "செய்", "நிறுத்து", "அழி", "பூட்டு", "பதிவிறக்கு",
    ];

    const startsWithQuestion = questionStarters.some((w) => inputLower.startsWith(w));
    const startsWithTask = taskStarters.some((w) => inputLower.startsWith(w));
    const hasQuestionMark = userInput.includes("?");

    if ((startsWithQuestion || hasQuestionMark) && !startsWithTask) {
      if ([IntentType.QUESTION, IntentType.RESEARCH, IntentType.DOCUMENTATION].includes(intent)) {
        return ["question", intent];
      }
      return ["question", IntentType.QUESTION];
    }

    const taskIntents: IntentType[] = [
      IntentType.CODE, IntentType.DEBUG, IntentType.SYSTEM_CONTROL,
      IntentType.AUTOMATION, IntentType.FILE_OPERATION, IntentType.APP_CONTROL,
      IntentType.BROWSER_AUTOMATION, IntentType.MULTI_STEP_ACTION,
      IntentType.YOUTUBE, IntentType.VOICE_COMMAND,
    ];

    if (startsWithTask || taskIntents.includes(intent)) {
      return ["task", intent];
    }

    if ([IntentType.QUESTION, IntentType.RESEARCH].includes(intent)) {
      return ["question", intent];
    }

    return ["chat", intent];
  }
}

// Singleton
export const intentClassifier = new IntentClassifier();
