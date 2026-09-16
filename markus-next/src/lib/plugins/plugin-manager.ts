/**
 * Markus AI — Plugin Management System (§8)
 * Direct port from plugins/plugin_manager.py.
 */

interface PluginMetadata {
  name: string;
  version: string;
  description: string;
  author: string;
  enabled: boolean;
  entryPoint: string | null;
  toolsProvided: string[];
}

class PluginManager {
  private _plugins: Map<string, PluginMetadata> = new Map();

  constructor() {
    console.log("Plugin Manager initialized");
  }

  registerPlugin(metadata: PluginMetadata): boolean {
    this._plugins.set(metadata.name, metadata);
    console.log(`Plugin registered: ${metadata.name} (v${metadata.version})`);
    return true;
  }

  listPlugins(): Record<string, unknown>[] {
    return Array.from(this._plugins.values()).map((p) => ({
      name: p.name,
      version: p.version,
      description: p.description,
      author: p.author,
      enabled: p.enabled,
      tools_provided: p.toolsProvided,
    }));
  }

  getPlugin(name: string): PluginMetadata | undefined {
    return this._plugins.get(name);
  }

  togglePlugin(name: string, enabled: boolean): boolean {
    const plugin = this._plugins.get(name);
    if (plugin) {
      plugin.enabled = enabled;
      console.log(`Plugin ${name} enabled status set to: ${enabled}`);
      return true;
    }
    return false;
  }
}

export const pluginManager = new PluginManager();
