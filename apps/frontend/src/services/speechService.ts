// Speech service integration using Azure Speech SDK
import * as speechsdk from 'microsoft-cognitiveservices-speech-sdk';
import { jwtDecode } from 'jwt-decode';

const tokenServicePrefix = import.meta.env.VITE_TOKEN_SERVICE_PREFIX;
const speechVoiceName = import.meta.env.VITE_SPEECH_VOICE_NAME;

if (!tokenServicePrefix) {
  console.error('VITE_TOKEN_SERVICE_PREFIX is not defined in the environment variables.');
}

// Create variables for speech token and region that can be refreshed
let speechToken: string;
let speechRegion: string;
let speechConfig: speechsdk.SpeechConfig;

// Helper functions for common operations
const handleAutoListenTimeout = (timeoutMs: number, recognizer: speechsdk.SpeechRecognizer, resolve: (value: string | null) => void): NodeJS.Timeout => {
  return setTimeout(() => {
    if (activeRecognizer === recognizer) {
      const currentRecognizer = activeRecognizer;
      activeRecognizer = null;
      currentRecognizer.close();
      resolve(null);
    }
  }, timeoutMs);
};

const cleanupAutoListenSession = (recognizer: any): void => {
  const autoListenData = recognizer.__autoListenData;
  if (autoListenData && autoListenData.timeout) {
    clearTimeout(autoListenData.timeout);
  }
};

// Unified error handler for speech recognition
const handleRecognitionError = (result: speechsdk.SpeechRecognitionResult): string => {
  let errorMessage = 'Speech recognition failed';

  if (result.reason === speechsdk.ResultReason.Canceled) {
    const cancellationDetails = speechsdk.CancellationDetails.fromResult(result);

    if (cancellationDetails.reason === speechsdk.CancellationReason.Error) {
      errorMessage = `Recognition error: ${cancellationDetails.errorDetails}`;
    }
  } else {
    console.log(`ERROR: Speech not recognized. Reason: ${result.reason}`);
  }

  return errorMessage;
};

// Token management functions
const isTokenExpired = (): boolean => {
  try {
    if (!speechToken) return true;

    const decoded = jwtDecode(speechToken) as { exp: number, region: string };
    const expirationTime = decoded.exp * 1000; // Convert to milliseconds
    return Date.now() >= expirationTime;
  } catch {
    // If we can't decode the token, assume it's expired
    return true;
  }
};

const ensureValidToken = async (): Promise<boolean> => {
  // Check if token exists and is not expired
  if (!speechToken || isTokenExpired()) {
    return await fetchSpeechToken();
  }
  return true;
};

// Event system for speech service errors
document.addEventListener("speech-service-error", ((e: CustomEvent<string>) => {
  console.error("Speech service error:", e.detail);
}) as EventListener);

// Helper function to emit speech service errors
export const emitSpeechError = (errorMessage: string): void => {
  const event = new CustomEvent("speech-service-error", { detail: errorMessage });
  document.dispatchEvent(event);
};

// Function to fetch and set up the speech token
const fetchSpeechToken = async (): Promise<boolean> => {
  try {
    const response = await fetch(`${tokenServicePrefix}/speech`, {method: 'POST'});
    const tokenData = await response.json();
    speechToken = tokenData.speech_token;
    speechRegion = jwtDecode(speechToken).region;

    // Initialize or update speech config
    speechConfig = speechsdk.SpeechConfig.fromAuthorizationToken(speechToken, speechRegion);
    speechConfig.speechSynthesisVoiceName = speechVoiceName;

    return true;
  } catch (error) {
    console.error('Failed to fetch speech token:', error);
    emitSpeechError('Failed to get speech token. Please check your connection and try again.');
    return false;
  }
};

// Initial token fetch - don't throw if it fails
try {
  await fetchSpeechToken();
} catch (error) {
  console.error('Initial token fetch failed, but app will continue:', error);
  emitSpeechError('Speech service initialization failed. Voice features may not work properly.');
}

// Define speech recognition functions
let activeRecognizer: speechsdk.SpeechRecognizer | null = null;

// Function to stop speech recognition
export const stopSpeechRecognition = (): Promise<string | null> => {
  return new Promise((resolve) => {
    if (activeRecognizer) {
      const currentRecognizer = activeRecognizer;

      // Check if this is an auto-listen session that needs special cleanup
      const autoListenData = (currentRecognizer as any).__autoListenData;
      if (autoListenData && autoListenData.isAutoListen) {
        // Use the helper function to clean up the timeout
        cleanupAutoListenSession(currentRecognizer);

        // Notify the auto-listen promise that we've stopped manually
        if (autoListenData.resolveFn) {
          // Resolve the autoStartListening promise with null to indicate manual stop
          autoListenData.resolveFn(null);
        }
      }

      // Close the recognizer and clear the reference
      currentRecognizer.close();
      activeRecognizer = null;

      // Since we can't reliably get the partial result, resolve with an empty string
      // The app will handle this case appropriately
      resolve("");
    } else {
      resolve(null);
    }
  });
};

export const startSpeechRecognition = async (): Promise<string> => {
  return new Promise(async (resolve, reject) => {
    try {
      if (!speechConfig) {
        const errorMessage = "Speech service is not initialized";
        emitSpeechError(errorMessage);
        reject(errorMessage);
        return;
      }

      // Setup audio config for the microphone
      const audioConfig = speechsdk.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new speechsdk.SpeechRecognizer(speechConfig, audioConfig);

      // Store active recognizer so it can be stopped later
      activeRecognizer = recognizer;

      // Process speech recognition results
      recognizer.recognizeOnceAsync((result) => {
        activeRecognizer = null; // Clear the reference after completion
        if (result.reason === speechsdk.ResultReason.RecognizedSpeech) {
          resolve(result.text);
        } else {
          // Use the unified error handler
          const errorMessage = handleRecognitionError(result);
          reject(errorMessage);
        }
      });
    } catch (error) {
      console.error('Error in speech recognition:', error);
      const errorMsg = error instanceof Error ? error.message : String(error);
      emitSpeechError(`Speech recognition failed: ${errorMsg}`);
      reject(error);
    }
  });
};

// Define text-to-speech function with token refresh capability
export const synthesizeSpeech = async (text: string, useTextToSpeech = true): Promise<void> => {
  // Skip speech synthesis if conditions aren't met
  if (!useTextToSpeech || !text) {
    const reason = !useTextToSpeech ? 'Speech is disabled in settings' : 'No text provided';
    console.log(`Speech synthesis skipped: ${reason}`);
    return Promise.resolve();
  }

  if (!speechConfig) {
    emitSpeechError('Speech service is not initialized. Please try again later.');
    console.log('Speech synthesis skipped: Speech configuration not available');
    return Promise.resolve();
  }

  // Ensure we have a valid token before attempting synthesis
  await ensureValidToken();

  // Use text directly without trying to parse it as JSON
  const speechText = text;

  // Function to perform speech synthesis with current token
  const performSpeechSynthesis = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      try {
        // Setup speech synthesizer
        const synthesizer = new speechsdk.SpeechSynthesizer(speechConfig);

        // Start speech synthesis
        synthesizer.speakTextAsync(
          speechText,
          (result) => {
            if (result.reason === speechsdk.ResultReason.SynthesizingAudioCompleted) {
              resolve();
            } else {
              console.log(`Speech synthesis failed: ${result.errorDetails}`);
              reject(`Speech synthesis failed: ${result.errorDetails}`);
            }
            synthesizer.close();
          },
          (err) => {
            console.log(`Speech synthesis error: ${err}`);

            // Check if error is related to authentication
            if (err.toString().includes('Authentication failed') ||
                err.toString().includes('Authorization failed') ||
                err.toString().includes('HTTP Authentication failed')) {
              console.log('Token authentication error detected');
              reject({ authError: true, message: err });
            } else {
              reject(`Speech synthesis error: ${err}`);
            }
            synthesizer.close();
          }
        );
      } catch (err) {
        console.error('Error setting up speech synthesizer:', err);
        resolve(); // Resolve anyway to prevent the app from breaking
      }
    });
  };

  try {
    // First attempt with current token
    return await performSpeechSynthesis();
  } catch (error: any) {
    // Check if this was an authentication error that needs token refresh
    if (error.authError) {
      console.log('Attempting to refresh speech token and retry...');
      try {
        // Refresh token and try again
        if (await fetchSpeechToken()) {
          return await performSpeechSynthesis();
        } else {
          console.warn('Speech synthesis skipped: Could not refresh token');
        }
      } catch (refreshError) {
        console.error('Failed to refresh token:', refreshError);
      }
    } else {
      // For other errors, just log them
      console.error('Speech synthesis error (continuing with text only):', error);
    }
    // Don't throw, just return to prevent disrupting the app
    return;
  }
};

// Function to extract voice summary from API response
export const extractVoiceSummaryFromResponse = (response: unknown): string | null => {
  if (!response) return null;

  try {
    // Convert string response to object if needed
    const responseObj = typeof response === 'string'
      ? JSON.parse(response)
      : response;

    // Look for voiceSummary at root level
    if (responseObj?.voiceSummary && typeof responseObj.voiceSummary === 'string') {
      return responseObj.voiceSummary;
    }

    // Look for voiceSummary in output property
    if (responseObj?.output?.voiceSummary && typeof responseObj.output.voiceSummary === 'string') {
      return responseObj.output.voiceSummary;
    }

    return null;
  } catch {
    console.error('Error extracting voice summary');
    return null;
  }
}

// Auto-listen function that starts recording and stops after 5 seconds if no speech is detected
export const autoStartListening = async (timeoutMs = 5000): Promise<string | null> => {
  if (!speechConfig) {
    console.warn('Auto-listening skipped: Speech configuration not available');
    return null;
  }

  // Track the current auto-listen session with a unique identifier
  let autoListenResolveFn: ((value: string | null) => void) | null = null;
  let autoListenTimeout: NodeJS.Timeout | null = null;

  return new Promise(async (resolve) => {
    // Store the resolve function so we can call it when stopSpeechRecognition is called
    autoListenResolveFn = resolve;

    // Setup audio config and recognizer
    const audioConfig = speechsdk.AudioConfig.fromDefaultMicrophoneInput();
    const recognizer = new speechsdk.SpeechRecognizer(speechConfig, audioConfig);

    // Store active recognizer with additional metadata for auto-listen
    activeRecognizer = recognizer;

    // Store additional metadata on the recognizer object for cleanup
    (recognizer as any).__autoListenData = {
      resolveFn: autoListenResolveFn,
      timeout: null,
      isAutoListen: true
    };

    // Set timeout for no speech detection using the helper function
    autoListenTimeout = handleAutoListenTimeout(timeoutMs, recognizer, resolve);

    // Store timeout reference for cleanup
    (recognizer as any).__autoListenData.timeout = autoListenTimeout;

    // Process recognition results
    recognizer.recognizeOnceAsync((result) => {
      // Get the timeout from the recognizer's metadata before clearing
      const metadata = (recognizer as any).__autoListenData;
      metadata?.timeout && clearTimeout(metadata.timeout);

      // Clear active recognizer only if it's still this one
      if (activeRecognizer === recognizer) {
        activeRecognizer = null;
      }

      if (result.reason === speechsdk.ResultReason.RecognizedSpeech) {
        resolve(result.text);
      } else {
        // Log specific error details only in detailed debug scenarios
        if (result.reason !== speechsdk.ResultReason.NoMatch) {
          console.log(`AUTO-ERROR: Speech recognition failed. Reason: ${result.reason}`);
        }
        resolve(null);
      }
    });
  }).catch(error => {
    console.error('Error in auto speech recognition:', error);
    return null;
  });
};

// Export the token refresh function so it can be called directly if needed
export const refreshSpeechToken = fetchSpeechToken;
