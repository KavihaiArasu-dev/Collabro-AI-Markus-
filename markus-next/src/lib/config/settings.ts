/**
 * Markus AI — Configuration Settings
 *
 * Centralized configuration loaded from environment variables with sensible defaults.
 * Direct port from config/settings.py.
 */

export interface OmniRouteSettings {
  baseUrl: string;
  apiKey: string;
  timeout: number;
  maxRetries: number;
}

export interface DatabaseSettings {
  url: string;
  host: string;
  port: number;
  username: string;
  password: string;
  dbname: string;
  echo: boolean;
}

export interface MemorySettings {
  dbPath: string;
}

export interface RAGSettings {
  embeddingModel: string;
  vectorStorePath: string;
  documentsPath: string;
  chunkSize: number;
  chunkOverlap: number;
  topK: number;
}

export interface VoiceSettings {
  language: string;
  ttsVoice: string;
  whisperLanguage: string;
}

export interface Settings {
  host: string;
  port: number;
  env: string;
  debug: boolean;
  secretKey: string;
  logLevel: string;
  logFile: string;
  omniroute: OmniRouteSettings;
  database: DatabaseSettings;
  memory: MemorySettings;
  rag: RAGSettings;
  voice: VoiceSettings;
  isDevelopment: boolean;
  isProduction: boolean;
}

function getEnv(key: string, defaultValue: string = ""): string {
  return process.env[key] ?? defaultValue;
}

function getEnvInt(key: string, defaultValue: number): number {
  const val = process.env[key];
  return val ? parseInt(val, 10) : defaultValue;
}

function getEnvBool(key: string, defaultValue: boolean): boolean {
  const val = process.env[key];
  if (!val) return defaultValue;
  return val.toLowerCase() === "true";
}

function createSettings(): Settings {
  const env = getEnv("MARKUS_ENV", "development");

  return {
    host: getEnv("MARKUS_HOST", "0.0.0.0"),
    port: getEnvInt("MARKUS_PORT", 8010),
    env,
    debug: getEnvBool("MARKUS_DEBUG", true),
    secretKey: getEnv("MARKUS_SECRET_KEY", "change-this-to-a-random-secret-key"),
    logLevel: getEnv("LOG_LEVEL", "INFO"),
    logFile: getEnv("LOG_FILE", "./logs/markus.log"),

    omniroute: {
      baseUrl: getEnv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1"),
      apiKey: getEnv("OMNIROUTE_API_KEY", ""),
      timeout: 120,
      maxRetries: 3,
    },

    database: {
      url: getEnv("DATABASE_URL", "mysql+pymysql://kavi:mvkagagb.@localhost:3306/markus"),
      host: getEnv("MYSQL_HOST", "localhost"),
      port: getEnvInt("MYSQL_PORT", 3306),
      username: getEnv("MYSQL_USERNAME", "kavi"),
      password: getEnv("MYSQL_PASSWORD", "mvkagagb."),
      dbname: getEnv("MYSQL_DBNAME", "markus"),
      echo: false,
    },

    memory: {
      dbPath: getEnv("MEMORY_DB_PATH", "./data/memory.db"),
    },

    rag: {
      embeddingModel: getEnv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
      vectorStorePath: getEnv("VECTOR_STORE_PATH", "./data/vector_store"),
      documentsPath: getEnv("DOCUMENTS_PATH", "./data/documents"),
      chunkSize: 512,
      chunkOverlap: 50,
      topK: 5,
    },

    voice: {
      language: getEnv("MARKUS_LANGUAGE", "ta-IN"),
      ttsVoice: getEnv("MARKUS_TTS_VOICE", "ta-IN-ValluvarNeural"),
      whisperLanguage: getEnv("MARKUS_WHISPER_LANGUAGE", "ta"),
    },

    get isDevelopment() {
      return this.env === "development";
    },
    get isProduction() {
      return this.env === "production";
    },
  };
}

// Singleton instance
export const settings = createSettings();
