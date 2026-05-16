import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { BlockData, BLOCK_COLORS } from '../../types/blocks';
import { t } from '../../i18n';

function trunc(text: string, max: number): string {
  if (!text) return '';
  return text.length > max ? text.substring(0, max) + '…' : text;
}

const CharacterBlock: React.FC<NodeProps<BlockData>> = ({ data, selected }) => {
  const content = data.content || {};
  const color = BLOCK_COLORS.CHARACTER;
  const completeness = data.completeness || 0;

  return (
    <div className={`block-node ${selected ? 'selected' : ''}`} style={{ borderColor: color, minWidth: 240 }}>
      <div className="block-header">
        <div className="block-type-icon" style={{ background: color }}>C</div>
        <div className="block-title">{content.name || t('char.new_character')}</div>
        <div className="block-completeness">
          <div className="block-completeness-fill" style={{
            height: `${completeness * 100}%`,
            background: completeness > 0.6 ? '#50C878' : completeness > 0.3 ? '#F39C12' : '#E74C3C',
          }} />
        </div>
      </div>
      {!data.collapsed && (
        <div className="block-content-preview">
          <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
            <span style={{ color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>{t('field.want')}:</span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{content.want || '?'}</span>
          </div>
          <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
            <span style={{ color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>{t('field.need')}:</span>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{content.need || '?'}</span>
          </div>
          {content.role_archetype && (
            <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
              <span style={{ color, opacity: 0.7, flexShrink: 0, fontSize: 10 }}>{t('field.role_archetype')}:</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{content.role_archetype}</span>
            </div>
          )}
          {content.fatal_flaw && (
            <div style={{ display: 'flex', gap: 4, lineHeight: 1.6 }}>
              <span style={{ color: '#E74C3C', opacity: 0.8, flexShrink: 0, fontSize: 10 }}>{t('field.fatal_flaw')}:</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{trunc(content.fatal_flaw, 25)}</span>
            </div>
          )}
        </div>
      )}
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
};

export default CharacterBlock;
