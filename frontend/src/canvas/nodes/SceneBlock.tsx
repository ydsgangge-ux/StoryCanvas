import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { BlockData, BLOCK_COLORS } from '../../types/blocks';

const SceneBlock: React.FC<NodeProps<BlockData>> = ({ data, selected }) => {
  const content = data.content || {};
  const color = BLOCK_COLORS.SCENE;

  return (
    <div className={`block-node ${selected ? 'selected' : ''}`} style={{ borderColor: color }}>
      <div className="block-header">
        <div className="block-type-icon" style={{ background: color }}>S</div>
        <div className="block-title">{content.title || '新场景'}</div>
        <div className="block-completeness">
          <div className="block-completeness-fill" style={{
            height: `${(data.completeness || 0) * 100}%`,
            background: (data.completeness || 0) > 0.6 ? '#50C878' : '#F39C12',
          }} />
        </div>
      </div>
      {!data.collapsed && (
        <div className="block-content-preview">
          {content.scene_goal && (
            <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
              <span style={{ color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>目标:</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{content.scene_goal}</span>
            </div>
          )}
          {content.emotion_target && (
            <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
              <span style={{ color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>情绪:</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{content.emotion_target}</span>
            </div>
          )}
          <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
            <span style={{ color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>张力:</span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {'█'.repeat(content.tension_level || 3)}{'░'.repeat(10 - (content.tension_level || 3))}
            </span>
          </div>
          {content.location_id && (
            <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
              <span style={{ color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>地点:</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{content.location_id}</span>
            </div>
          )}
        </div>
      )}
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
};

export default SceneBlock;
