import React from 'react';
import { CATEGORY_LABELS } from '../../types/blocks';

interface ProgressBarProps {
  overall: number;
  categories: Record<string, number>;
  status: string;
  level: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  world: '#7B68EE',
  character: '#4A90D9',
  structure: '#50C878',
  tension: '#E8873A',
};

const ProgressBar: React.FC<ProgressBarProps> = ({ overall, categories, status, level }) => {
  const levelIcons = ['⚡', '⚡', '✓', '✓✓', '✓✓✓'];

  return (
    <div className="progress-bar-container">
      <div className="progress-dimensions">
        {Object.entries(categories).map(([key, value]) => (
          <div className="progress-dim" key={key}>
            <span>{CATEGORY_LABELS[key] || key}</span>
            <div className="progress-dim-bar">
              <div
                className="progress-dim-fill"
                style={{ width: `${Math.min(value * 100, 100)}%`, background: CATEGORY_COLORS[key] || '#4A90D9' }}
              />
            </div>
            <span style={{ fontSize: 11, color: '#a0a0b0' }}>{Math.round(value * 100)}%</span>
          </div>
        ))}
      </div>
      <div className="progress-overall">
        <span>综合可控度</span>
        <div className="progress-overall-bar">
          <div
            className="progress-overall-fill"
            style={{ width: `${Math.min(overall * 100, 100)}%` }}
          />
        </div>
        <span style={{ width: 40, textAlign: 'right' }}>{Math.round(overall * 100)}%</span>
        <span className="progress-status" style={{ marginLeft: 8 }}>
          {levelIcons[level] || '⚡'} {status}
        </span>
      </div>
    </div>
  );
};

export default ProgressBar;
