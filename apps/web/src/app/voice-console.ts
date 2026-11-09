import { InjectionToken } from '@angular/core';

interface RecognitionEventLike { results: ArrayLike<{ 0: { transcript: string } }> }
interface RecognitionLike {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: RecognitionEventLike) => void) | null;
  onerror: (() => void) | null; onend: (() => void) | null;
  start(): void; stop(): void;
}
type RecognitionConstructor = new () => RecognitionLike;

export interface VoiceConsolePort {
  canSpeak: boolean;
  canListen: boolean;
  speak(message: string): void;
  listen(): Promise<string>;
  stop(): void;
}

class BrowserVoiceConsole implements VoiceConsolePort {
  private recognition: RecognitionLike | null = null;
  readonly canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;
  readonly canListen = typeof window !== 'undefined' && Boolean(
    (window as Window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor }).SpeechRecognition ??
    (window as Window & { webkitSpeechRecognition?: RecognitionConstructor }).webkitSpeechRecognition);

  speak(message: string): void {
    if (!this.canSpeak) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = 'pt-BR'; utterance.rate = 1; utterance.pitch = 0.95;
    window.speechSynthesis.speak(utterance);
  }

  listen(): Promise<string> {
    if (!this.canListen) return Promise.reject(new Error('speech_recognition_unavailable'));
    this.stop();
    const browser = window as Window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
    const Constructor = browser.SpeechRecognition ?? browser.webkitSpeechRecognition!;
    const recognition = new Constructor(); this.recognition = recognition;
    recognition.lang = 'pt-BR'; recognition.continuous = false; recognition.interimResults = false;
    return new Promise((resolve, reject) => {
      recognition.onresult = event => resolve(event.results[0]?.[0]?.transcript?.trim() ?? '');
      recognition.onerror = () => reject(new Error('speech_recognition_failed'));
      recognition.onend = () => { if (this.recognition === recognition) this.recognition = null; };
      recognition.start();
    });
  }

  stop(): void {
    this.recognition?.stop(); this.recognition = null;
    if (this.canSpeak) window.speechSynthesis.cancel();
  }
}

export const VOICE_CONSOLE = new InjectionToken<VoiceConsolePort>('voice console', {
  providedIn: 'root', factory: () => new BrowserVoiceConsole()
});
