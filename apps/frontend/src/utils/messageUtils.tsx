export const playSpeechResponse = async (response: any, speechService: any, useTextToSpeech: boolean) => {
  if (!useTextToSpeech) {
    console.log('Text to Speech is disabled, skipping audio playback');
    return;
  }

  try {
    const voiceSummary = speechService.extractVoiceSummaryFromResponse(response);
    if (voiceSummary) {
      await speechService.synthesizeSpeech(voiceSummary);
    } else if (response.inputMessage.content && typeof response.content === 'string') {
      await speechService.synthesizeSpeech(response.inputMessage.content);
    } else if (response.output?.displayResponse) {
      await speechService.synthesizeSpeech(response.output.displayResponse);
    }
  } catch (error) {
    console.error('Error playing voice response:', error);
  }
};

export const handleStreamingChunk = (
  chunk: string,
  updateOrAddBotMessage: (content: string) => void
) => {
  // Skip empty chunks
  if (!chunk || chunk.trim() === '') return;

  // Log the chunk for debugging
  console.log('Processing chunk:', chunk);

  try {
    // Update messages with chunk
    updateOrAddBotMessage(chunk);
  } catch (error) {
    console.error('Error handling streaming chunk:', error);
  }
};
