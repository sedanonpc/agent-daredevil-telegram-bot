/**
 * Frontend TTS Helper for Agent Daredevil API
 * ===========================================
 * 
 * This helper provides text-to-speech functionality for the frontend,
 * eliminating the need for backend voice processing and reducing API overhead.
 * 
 * Usage:
 * 1. Include this script in your frontend
 * 2. Call speakText() with the response from the API
 * 3. Configure voice settings as needed
 */

class AgentDaredevilTTS {
    constructor() {
        this.synthesis = window.speechSynthesis;
        this.voices = [];
        this.selectedVoice = null;
        this.isEnabled = true;
        
        // Load available voices
        this.loadVoices();
        
        // Re-load voices when they become available
        if (this.synthesis.onvoiceschanged !== undefined) {
            this.synthesis.onvoiceschanged = () => this.loadVoices();
        }
    }
    
    loadVoices() {
        this.voices = this.synthesis.getVoices();
        
        // Prefer English voices, fallback to first available
        const englishVoices = this.voices.filter(voice => 
            voice.lang.startsWith('en')
        );
        
        if (englishVoices.length > 0) {
            // Prefer male voices for Agent Daredevil character
            const maleVoices = englishVoices.filter(voice => 
                voice.name.toLowerCase().includes('male') ||
                voice.name.toLowerCase().includes('man') ||
                voice.name.toLowerCase().includes('david') ||
                voice.name.toLowerCase().includes('alex')
            );
            
            this.selectedVoice = maleVoices.length > 0 ? maleVoices[0] : englishVoices[0];
        } else if (this.voices.length > 0) {
            this.selectedVoice = this.voices[0];
        }
    }
    
    /**
     * Speak the given text using browser's built-in TTS
     * @param {string} text - Text to speak
     * @param {Object} options - Voice options
     */
    speakText(text, options = {}) {
        if (!this.isEnabled || !text) {
            return;
        }
        
        // Stop any current speech
        this.synthesis.cancel();
        
        // Create speech utterance
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Configure voice
        if (this.selectedVoice) {
            utterance.voice = this.selectedVoice;
        }
        
        // Configure speech parameters
        utterance.rate = options.rate || 1.0;        // Speech rate (0.1 to 10)
        utterance.pitch = options.pitch || 1.0;      // Voice pitch (0 to 2)
        utterance.volume = options.volume || 1.0;     // Volume (0 to 1)
        utterance.lang = options.lang || 'en-US';     // Language
        
        // Event handlers
        utterance.onstart = () => {
            console.log('Agent Daredevil TTS: Started speaking');
        };
        
        utterance.onend = () => {
            console.log('Agent Daredevil TTS: Finished speaking');
        };
        
        utterance.onerror = (event) => {
            console.error('Agent Daredevil TTS Error:', event.error);
        };
        
        // Speak the text
        this.synthesis.speak(utterance);
    }
    
    /**
     * Stop current speech
     */
    stopSpeaking() {
        this.synthesis.cancel();
    }
    
    /**
     * Pause current speech
     */
    pauseSpeaking() {
        this.synthesis.pause();
    }
    
    /**
     * Resume paused speech
     */
    resumeSpeaking() {
        this.synthesis.resume();
    }
    
    /**
     * Check if currently speaking
     */
    isSpeaking() {
        return this.synthesis.speaking;
    }
    
    /**
     * Enable/disable TTS
     */
    setEnabled(enabled) {
        this.isEnabled = enabled;
        if (!enabled) {
            this.stopSpeaking();
        }
    }
    
    /**
     * Get available voices
     */
    getVoices() {
        return this.voices;
    }
    
    /**
     * Set preferred voice
     */
    setVoice(voiceName) {
        const voice = this.voices.find(v => v.name === voiceName);
        if (voice) {
            this.selectedVoice = voice;
        }
    }
    
    /**
     * Get current voice settings
     */
    getVoiceSettings() {
        return {
            voice: this.selectedVoice ? this.selectedVoice.name : 'Default',
            voices: this.voices.map(v => ({
                name: v.name,
                lang: v.lang,
                default: v.default
            }))
        };
    }
}

// Global instance
window.agentDaredevilTTS = new AgentDaredevilTTS();

// Convenience functions
window.speakText = (text, options) => window.agentDaredevilTTS.speakText(text, options);
window.stopSpeaking = () => window.agentDaredevilTTS.stopSpeaking();
window.isSpeaking = () => window.agentDaredevilTTS.isSpeaking();

// Example usage:
/*
// Basic usage
speakText("Hello, I'm Agent Daredevil! What's the intel?");

// With custom settings
speakText("Mission accomplished!", {
    rate: 0.9,      // Slightly slower
    pitch: 0.8,     // Lower pitch
    volume: 0.8     // Quieter
});

// Check if speaking
if (isSpeaking()) {
    console.log("Agent is currently speaking");
}

// Stop speaking
stopSpeaking();
*/
