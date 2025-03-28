import React from 'react';

interface HumanIconProps {
  size?: number;
  color?: string;
  className?: string;
}

export const HumanIcon: React.FC<HumanIconProps> = ({ 
  size = 32, 
  color = '#FF4B4B', // Streamlit's primary red color
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
      <circle cx="12" cy="8" r="3.5" fill={color} />
      <path 
        d="M12 12.5c-3.5 0-6.5 2-6.5 5.5h13c0-3.5-3-5.5-6.5-5.5z" 
        fill={color} 
      />
    </svg>
  );
};

export default HumanIcon;