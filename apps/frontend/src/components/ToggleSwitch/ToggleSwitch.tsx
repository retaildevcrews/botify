import './ToggleSwitch.css';

interface ToggleSwitchProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

const ToggleSwitch: React.FC<ToggleSwitchProps> = ({ id, label, checked, onChange }) => {
  return (
    <div className="toggle-container">
      <label className="toggle-label" htmlFor={id}>{label}</label>
      <div className="switch">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="slider round" onClick={() => onChange(!checked)}></span>
      </div>
    </div>
  );
};

export default ToggleSwitch;
