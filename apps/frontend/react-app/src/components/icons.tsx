import React from 'react';

interface IconProps {
  size?: number;
  color?: string;
}

export const HumanIcon: React.FC<IconProps> = ({ size = 24, color = '#FF9999' }) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Square background with rounded corners */}
    <rect 
      x="2" 
      y="2" 
      width="20" 
      height="20" 
      rx="4" 
      fill="#FF9999" 
      stroke="black" 
      strokeWidth="1.5" 
    />
    {/* Person icon inside */}
    <path 
      d="M12 10.5C13.6569 10.5 15 9.15685 15 7.5C15 5.84315 13.6569 4.5 12 4.5C10.3431 4.5 9 5.84315 9 7.5C9 9.15685 10.3431 10.5 12 10.5Z" 
      stroke="black" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    />
    <path 
      d="M7 19.5V18C7 16.9391 7.42143 15.9217 8.17157 15.1716C8.92172 14.4214 9.93913 14 11 14H13C14.0609 14 15.0783 14.4214 15.8284 15.1716C16.5786 15.9217 17 16.9391 17 18V19.5" 
      stroke="black" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    />
  </svg>
);

export const BotIcon: React.FC<IconProps> = ({ size = 24, color = '#FFCC00' }) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Square background with rounded corners */}
    <rect 
      x="2" 
      y="2" 
      width="20" 
      height="20" 
      rx="4" 
      fill="#FFCC00" 
      stroke="black" 
      strokeWidth="1.5" 
    />
    {/* Bot face */}
    <rect 
      x="5" 
      y="7" 
      width="14" 
      height="10" 
      rx="2" 
      stroke="black" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
    />
    {/* Bot eyes */}
    <circle cx="9" cy="12" r="1.5" fill="black" />
    <circle cx="15" cy="12" r="1.5" fill="black" />
    {/* Bot antenna */}
    <path 
      d="M9 4.5L9 7" 
      stroke="black" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
    />
    <path 
      d="M15 4.5L15 7" 
      stroke="black" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
    />
    {/* Bot mouth/interface line */}
    <path 
      d="M7 15L17 15" 
      stroke="black" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
    />
  </svg>
);