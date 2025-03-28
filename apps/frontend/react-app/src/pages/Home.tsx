import React from 'react';
import ReactMarkdown from 'react-markdown';

const Home: React.FC = () => {
  return (
    <div className="home-container">
      <h2 className="home-header">Botify</h2>
      <hr className="divider" />
      <div className="home-content">
        <ReactMarkdown>
          {`
This app uses Azure Cognitive Search and Azure OpenAI to provide answers and
suggestions about your next favorite example!

### Want to learn more?
- Check out the [GitHub Repository](https://github.com/retaildevcrews/botify/)
- Ask a question or submit a [GitHub Issue](https://github.com/retaildevcrews/botify/issues/new)!
          `}
        </ReactMarkdown>
      </div>
      <hr className="divider" />
    </div>
  );
};

export default Home;