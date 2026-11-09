import { InjectionToken } from '@angular/core';

export interface VoiceConsolePort {
  canSpeak: boolean;
  canListen: boolean;
  speak(message: string): void;
  listen(): Promise<string>;
  stop(): void;
}

class PrivateVoiceConsole implements VoiceConsolePort {
  // Browser speech providers cannot currently guarantee local processing.
  readonly canSpeak = false;
  readonly canListen = false;
  speak(_message: string): void { }
  listen(): Promise<string> {
    return Promise.reject(new Error('voice_disabled_by_privacy_policy'));
  }
  stop(): void { }
}

export const VOICE_CONSOLE = new InjectionToken<VoiceConsolePort>('voice console', {
  providedIn: 'root', factory: () => new PrivateVoiceConsole()
});
