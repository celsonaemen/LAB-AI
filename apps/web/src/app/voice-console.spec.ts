import { TestBed } from '@angular/core/testing';
import { VOICE_CONSOLE } from './voice-console';

describe('Private voice boundary', () => {
  it('blocks browser speech and microphone APIs even when installed', async () => {
    const speak = spyOn(window.speechSynthesis, 'speak');
    const browser = window as Window & { webkitSpeechRecognition?: unknown };
    const previous = browser.webkitSpeechRecognition;
    const recognition = jasmine.createSpy('recognition');
    browser.webkitSpeechRecognition = recognition;
    try {
      const voice = TestBed.inject(VOICE_CONSOLE);
      expect(voice.canSpeak).toBeFalse();
      expect(voice.canListen).toBeFalse();
      voice.speak('private-test');
      await expectAsync(voice.listen()).toBeRejectedWithError('voice_disabled_by_privacy_policy');
      expect(speak).not.toHaveBeenCalled();
      expect(recognition).not.toHaveBeenCalled();
    } finally {
      browser.webkitSpeechRecognition = previous;
    }
  });
});
