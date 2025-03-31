import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  getOrCreateIds, 
  processSingleQuestion, 
  parseSearchDocumentChunk, 
  SearchDocument, 
  SingleQuestionResponse 
} from '../helpers/api';

const SingleQuestion: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState<SingleQuestionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sessionId, userId } = getOrCreateIds();

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      const result = await processSingleQuestion(question, sessionId, userId);
      setResponse(result);
    } catch (err: unknown) {
      setError('Failed to process your question. Please try again.');
      console.error('Error processing question:', err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const renderSearchResult = (document: SearchDocument, index: number): React.ReactNode => {
    // Use optional chaining instead of conditional checks
    const { title, location, chunk } = document.page_content ?? {};
    
    // Return null if title doesn't exist
    if (!title) return null;

    const { summary, content } = parseSearchDocumentChunk(chunk ?? '');

    // Create a document-specific unique ID instead of using array index
    const resultId = `result-${title.replace(/\s+/g, '-')}-${index}`;
    
    return (
      <div key={resultId} className="search-result">
        <h4 className="result-title">
          <a href={location} target="_blank" rel="noopener noreferrer" aria-label={`Open document: ${title}`}>
            {title}
          </a>
        </h4>
        {summary && <p className="result-summary"><strong>Summary:</strong> {summary}</p>}
        {content && <p className="result-content"><strong>Content:</strong> {content}</p>}
      </div>
    );
  };

  return (
    <div className="page-container">
      <h2 className="page-title">Q&A Search</h2>
      <div className="question-container">
        <form onSubmit={handleSubmit} className="question-form">
          <label htmlFor="question-input" className="sr-only">Your question</label>
          <input
            id="question-input"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Enter your question here..."
            className="input-field question-input"
            disabled={isLoading}
            aria-required="true"
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={isLoading || !question.trim()}
            aria-label="Submit question"
          >
            Ask
          </button>
        </form>

        {isLoading && <div className="spinner" aria-label="Loading results"></div>}
        {error && <div className="error-message" role="alert">{error}</div>}
        
        {response && (
          <div className="response-container">
            <div className="answer-container">
              <h3 className="answer-title">Answer</h3>
              <div className="answer-content">
                <ReactMarkdown>{response.answer}</ReactMarkdown>
              </div>
            </div>
            
            <div className="search-results">
              <h3 className="results-title">Search Results</h3>
              {response.search_documents && response.search_documents.length > 0 ? (
                response.search_documents.map((doc, index) => renderSearchResult(doc, index))
              ) : (
                <div className="no-results">No search results found</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SingleQuestion;