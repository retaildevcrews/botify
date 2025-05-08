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

// Function to fetch and set up the speech token
const fetchSpeechToken = async (): Promise<void> => {
  try {
    const response = await fetch(`${tokenServicePrefix}/speech`, {method: 'POST'});
    const tokenData = await response.json();
    speechToken = tokenData.speech_token;
    speechRegion = jwtDecode(speechToken).region;

    // Initialize or update speech config
    speechConfig = speechsdk.SpeechConfig.fromAuthorizationToken(speechToken, speechRegion);
    speechConfig.speechSynthesisVoiceName = speechVoiceName;

    console.log('Speech token refreshed successfully');
  } catch (error) {
    console.error('Failed to fetch speech token:', error);
    throw error;
  }
};

// Initial token fetch
await fetchSpeechToken();

// Define speech recognition functions
let activeRecognizer: speechsdk.SpeechRecognizer | null = null;

// Function to stop speech recognition
export const stopSpeechRecognition = (): Promise<string | null> => {
  return new Promise((resolve) => {
    if (activeRecognizer) {
      console.log('Stopping speech recognition...');

      // We can't directly get partial results from recognizeOnceAsync
      // But we can stop and close the recognizer to force it to return any partial results
      activeRecognizer.close();
      activeRecognizer = null;
      console.log('Recognition stopped');

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
      // Setup audio config for the microphone
      const audioConfig = speechsdk.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new speechsdk.SpeechRecognizer(speechConfig, audioConfig);

      // Store active recognizer so it can be stopped later
      activeRecognizer = recognizer;

      // Start listening
      console.log('Listening...');

      // Process speech recognition results
      recognizer.recognizeOnceAsync((result) => {
        activeRecognizer = null; // Clear the reference after completion
        if (result.reason === speechsdk.ResultReason.RecognizedSpeech) {
          console.log(`RECOGNIZED: ${result.text}`);
          resolve(result.text);
        } else {
          console.log(`ERROR: Speech not recognized. Reason: ${result.reason}`);
          if (result.reason === speechsdk.ResultReason.Canceled) {
            const cancellationDetails = speechsdk.CancellationDetails.fromResult(result);
            console.log(`CANCELED: Reason=${cancellationDetails.reason}`);
            if (cancellationDetails.reason === speechsdk.CancellationReason.Error) {
              console.log(`CANCELED: ErrorCode=${cancellationDetails.ErrorCode}`);
              console.log(`CANCELED: ErrorDetails=${cancellationDetails.errorDetails}`);
            }
          }
          reject('Speech recognition failed');
        }
      });
    } catch (error) {
      console.error('Error in speech recognition:', error);
      reject(error);
    }
  });
};

// Define text-to-speech function with token refresh capability
export const synthesizeSpeech = async (text: string): Promise<void> => {
  if (!text) {
    return Promise.reject('No text provided for speech synthesis');
  }

  // Extract voice summary if it's contained in JSON response
  let speechText = text;
  try {
    const jsonData = JSON.parse(text);
    if (jsonData && jsonData.voiceSummary) {
      speechText = jsonData.voiceSummary;
    }
  } catch {
    // Not JSON, use the original text
    console.log('Using original text for speech synthesis');
  }

  // Function to perform speech synthesis with current token
  const performSpeechSynthesis = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      // Setup speech synthesizer
      const synthesizer = new speechsdk.SpeechSynthesizer(speechConfig);

      // Start speech synthesis
      synthesizer.speakTextAsync(
        speechText,
        (result) => {
          if (result.reason === speechsdk.ResultReason.SynthesizingAudioCompleted) {
            console.log('Speech synthesis completed');
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
        await fetchSpeechToken();
        return await performSpeechSynthesis();
      } catch (refreshError) {
        console.error('Failed to refresh token:', refreshError);
        throw new Error('Failed to refresh speech token');
      }
    } else {
      // For other errors, just throw them
      throw error;
    }
  }
};

// Function to extract voice summary from API response
export const extractVoiceSummaryFromResponse = (response: unknown): string | null => {
  if (!response) return null;

  try {
    if (typeof response === 'string') {
      try {
        const parsedResponse = JSON.parse(response) as Record<string, unknown>;
        return (parsedResponse.voiceSummary as string) || null;
      } catch {
        return null;
      }
    } else if (typeof response === 'object' && response !== null) {
      const typedResponse = response as Record<string, unknown>;
      if (typedResponse.voiceSummary && typeof typedResponse.voiceSummary === 'string') {
        return typedResponse.voiceSummary;
      } else if (typedResponse.output && typeof typedResponse.output === 'object' && typedResponse.output !== null) {
        const output = typedResponse.output as Record<string, unknown>;
        if (output.voiceSummary && typeof output.voiceSummary === 'string') {
          return output.voiceSummary;
        }
      }
    }
  } catch {
    console.error('Error extracting voice summary');
  }

  return null;
}

// Export the token refresh function so it can be called directly if needed
export const refreshSpeechToken = fetchSpeechToken;
