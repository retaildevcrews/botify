import React from 'react';

interface BotIconProps {
  size?: number;
  color?: string;
  className?: string;
}

export const BotIcon: React.FC<BotIconProps> = ({ 
  size = 32, 
  color = '#0068C9', // Streamlit's blue accent color
  className = '' 
}) => {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="12" cy="12" r="11" fill="white" stroke={color} strokeWidth="2" />
      <rect x="7" y="9" width="10" height="7" rx="1" fill={color} />
      <rect x="9" y="16" width="6" height="1.5" fill={color} />
      <circle cx="9" cy="11.5" r="1.25" fill="white" />
      <circle cx="15" cy="11.5" r="1.25" fill="white" />
      <rect x="10" y="6.5" width="4" height="2.5" fill={color} />
    </svg>
  );
};

export default BotIcon;