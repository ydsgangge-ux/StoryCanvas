import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore'
import { useT } from '../i18n/useT';;
import { StoryCard } from '../types/canvas';

interface StoryCardPickerProps {
  projectId: string;
  onClose: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  A: '目标驱动', B: '关系驱动', C: '揭秘驱动',
  D: '生存驱动', E: '成长驱动', F: '世界驱动', G: '特殊结构',
};

const CATEGORY_COLORS: Record<string, string> = {
  A: '#4A90D9', B: '#FF69B4', C: '#E8873A',
  D: '#E74C3C', E: '#50C878', F: '#7B68EE', G: '#FFD700',
};

const StoryCardPicker: React.FC<StoryCardPickerProps> = ({ projectId, onClose }) => {
  const { storyCards, loadStoryCards, applyStoryCards, isLoading } = useProjectStore();
  const [selectedPrimary, setSelectedPrimary] = useState<string | null>(null);
  const [selectedSecondary, setSelectedSecondary] = useState<string[]>([]);

  useEffect(() => {
    loadStoryCards();
  }, []);

  const groupedCards: Record<string, StoryCard[]> = {};
  storyCards.forEach((card) => {
    if (!groupedCards[card.category]) groupedCards[card.category] = [];
    groupedCards[card.category].push(card);
  });

  const handleCardClick = (cardId: string) => {
    if (selectedPrimary === cardId) {
      setSelectedPrimary(null);
    } else {
      setSelectedPrimary(cardId);
    }
  };

  const handleSecondaryToggle = (cardId: string) => {
    if (selectedSecondary.includes(cardId)) {
      setSelectedSecondary(selectedSecondary.filter((id) => id !== cardId));
    } else {
      setSelectedSecondary([...selectedSecondary, cardId]);
    }
  };

  const handleApply = async () => {
    if (!selectedPrimary) return;
    await applyStoryCards(projectId, selectedPrimary, selectedSecondary);
    onClose();
  };

  return (
    <div className="story-card-picker-overlay">
      <div className="story-card-picker">
        <div className="story-card-picker-header">
          <h2>选择故事卡</h2>
          <p>故事卡会为你的项目自动创建初始结构和推荐块。选择一个主卡，可以叠加副卡。</p>
        </div>
        <div className="story-card-grid">
          {Object.entries(groupedCards).map(([category, cards]) => (
            <div key={category} style={{ gridColumn: '1 / -1' }}>
              <div style={{
                fontSize: 13, fontWeight: 600, color: CATEGORY_COLORS[category] || '#fff',
                marginBottom: 8, paddingLeft: 4,
              }}>
                {CATEGORY_LABELS[category] || category}
              </div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {cards.map((card) => {
                  const isPrimary = selectedPrimary === card.id;
                  const isSecondary = selectedSecondary.includes(card.id);
                  const isSelected = isPrimary || isSecondary;

                  return (
                    <div
                      key={card.id}
                      className={`story-card-item ${isPrimary ? 'selected' : ''}`}
                      style={{ flex: '1 1 200px', opacity: isPrimary ? 1 : isSecondary ? 0.9 : 0.85 }}
                      onClick={() => handleCardClick(card.id)}
                    >
                      <div className="card-name">{card.name}</div>
                      <div className="card-category">
                        {CATEGORY_LABELS[card.category]} · {card.id}
                      </div>
                      <div className="card-desc">{card.description}</div>
                      <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <span className={`card-difficulty difficulty-${card.difficulty}`}>
                          {card.difficulty === 'beginner' ? '初级' :
                           card.difficulty === 'intermediate' ? '中级' :
                           card.difficulty === 'advanced' ? '高级' : '专家'}
                        </span>
                        {isPrimary && <span style={{ fontSize: 10, color: '#FFD700' }}>★ 主卡</span>}
                      </div>
                      {card.reference_works && card.reference_works.length > 0 && (
                        <div style={{ fontSize: 10, color: '#6c6c80', marginTop: 4 }}>
                          参考: {card.reference_works.join(', ')}
                        </div>
                      )}
                      {selectedPrimary && selectedPrimary !== card.id && (
                        <button
                          className="btn btn-sm btn-ghost"
                          style={{ marginTop: 6, fontSize: 11 }}
                          onClick={(e) => { e.stopPropagation(); handleSecondaryToggle(card.id); }}
                        >
                          {isSecondary ? '取消叠加' : '+ 叠加'}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <div className="story-card-picker-footer">
          <button className="btn" onClick={onClose}>
            空白画布
          </button>
          <button
            className="btn btn-primary"
            onClick={handleApply}
            disabled={!selectedPrimary || isLoading}
          >
            {isLoading ? '应用...' : `应用故事卡 (${selectedSecondary.length + (selectedPrimary ? 1 : 0)}张)`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default StoryCardPicker;
