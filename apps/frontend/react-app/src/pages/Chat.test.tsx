import React from 'react';
import { render, screen } from '@testing-library/react';
import Chat from './Chat';

describe('Chat Component', () => {
  it('renders the chat title', () => {
    render(<Chat />);
    const titleElement = screen.getByText(/Chat with Botify/i);
    expect(titleElement).toBeInTheDocument();
  });
});