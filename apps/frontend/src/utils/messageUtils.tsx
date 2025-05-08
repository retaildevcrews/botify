export const playSpeechResponse = async (response: any, speechService: any) => {
  try {
    const voiceSummary = speechService.extractVoiceSummaryFromResponse(response);
    if (voiceSummary) {
      await speechService.synthesizeSpeech(voiceSummary);
    } else if (response.inputMessage.content) {
      await speechService.synthesizeSpeech(response.inputMessage.content);
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
