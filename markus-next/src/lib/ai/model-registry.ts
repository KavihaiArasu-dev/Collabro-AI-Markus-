/**
 * Markus AI — Model Registry (§6a)
 *
 * Maps Markus modes to OmniRoute routing aliases.
 */

import { RouteAlias, MODEL_PROFILES } from "@/lib/config/constants";

class ModelRegistry {
  private _profiles: Record<string, { route: RouteAlias; description: string }>;
  private _profilesCopy: Record<string, { route: RouteAlias; description: string }>;
  private _availableModels: Record<string, unknown>[] = [];

  constructor() {
    this._profiles = { ...MODEL_PROFILES };
    this._profilesCopy = { ...this._profiles };
    console.log(`Model registry initialized with ${Object.keys(this._profiles).length} profiles`);
  }

  getRoute(profileName: string): string {
    const profile = this._profiles[profileName];
    if (profile) {
      return profile.route;
    }
    console.warn(`Unknown profile '${profileName}', falling back to 'auto'`);
    return RouteAlias.AUTO;
  }

  getProfile(profileName: string): { route: RouteAlias; description: string } | undefined {
    return this._profiles[profileName];
  }

  listProfiles(): Record<string, { route: RouteAlias; description: string }> {
    return this._profilesCopy;
  }

  registerProfile(name: string, route: string, description: string = ""): void {
    this._profiles[name] = { route: route as RouteAlias, description };
    this._profilesCopy = { ...this._profiles };
    console.log(`Registered model profile: ${name} → ${route}`);
  }

  updateAvailableModels(models: Record<string, unknown>[]): void {
    this._availableModels = models;
    console.log(`Updated available models: ${models.length} models`);
  }

  getAvailableModels(): Record<string, unknown>[] {
    return this._availableModels;
  }
}

// Singleton
export const modelRegistry = new ModelRegistry();
