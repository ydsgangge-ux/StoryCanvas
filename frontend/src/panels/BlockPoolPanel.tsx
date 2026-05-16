import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useCanvasStore } from '../store/canvasStore';
import { useUIStore } from '../store/uiStore';
import { BLOCK_COLORS, BLOCK_CATEGORIES } from '../types/blocks';
import { useT } from '../i18n/useT';
import { t } from '../i18n';

interface PoolBlock {
  id: string;
  type: string;
  content: any;
  completeness: number;
  canvas_x: number;
  canvas_y: number;
}

const CATEGORY_ORDER = ['character', 'world', 'structure', 'tension'];

const BlockPoolPanel: React.FC = () => {
  const { currentProject } = useProjectStore();
  const { syncFromBlocks } = useCanvasStore();
  const { showToast, setShowBlockEditor, setShowStoryCardPicker } = useUIStore();
  const [poolBlocks, setPoolBlocks] = useState<PoolBlock[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (currentProject) fetchPool();
  }, [currentProject?.id]);

  const fetchPool = async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/pool-blocks`);
      if (res.ok) setPoolBlocks(await res.json());
    } catch {}
    setLoading(false);
  };

  const moveToCanvas = async (block: PoolBlock) => {
    try {
      await fetch(`/api/projects/${currentProject!.id}/blocks/${block.id}/move-to-canvas`, { method: 'POST' });
      showToast(`${t(`block.${block.type}`)} ${t('pool.placed_on_canvas')}`);
      await fetchPool();
      // 刷新画布
      const { blocks, connections } = useProjectStore.getState();
      syncFromBlocks(blocks, connections);
    } catch {
      showToast(t('pool.operation_failed'), 'error');
    }
  };

  const deleteBlock = async (blockId: string) => {
    if (!confirm(t('pool.confirm_delete'))) return;
    try {
      await fetch(`/api/projects/${currentProject!.id}/blocks/${blockId}`, { method: 'DELETE' });
      showToast(t('pool.deleted'));
      fetchPool();
    } catch {}
  };

  const filtered = poolBlocks.filter(b => {
    const label = t(`block.${b.type}`);
    const name = b.content?.name || b.content?.title || '';
    return label.includes(search) || name.includes(search) || b.type.includes(search.toUpperCase());
  });

  // 按类别分组
  const grouped: Record<string, PoolBlock[]> = {};
  for (const b of filtered) {
    const cat = BLOCK_CATEGORIES[b.type] || 'structure';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(b);
  }

  return (
    <div className="panel" style={{ width: 320, minWidth: 260 }}>
      <div className="panel-header">
        <span>📦 {t('pool.title')}</span>
        <button className="btn btn-sm btn-ghost" onClick={fetchPool} disabled={loading}>⟳</button>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        {/* 搜索 */}
        <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border-color)' }}>
          <input className="form-input" type="text" placeholder={`🔍 ${t('pool.search_placeholder')}...`}
            value={search} onChange={(e) => setSearch(e.target.value)}
            style={{ fontSize: 12, padding: '4px 8px' }} />
        </div>

        {/* 统计 */}
        <div style={{ padding: '4px 10px', fontSize: 11, color: '#888', borderBottom: '1px solid var(--border-color)' }}>
          {t('pool.total_blocks', { count: poolBlocks.length })}
        </div>

        {/* 列表 */}
        <div style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto', padding: 8 }}>
          {loading ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20 }}>{t('pool.loading')}</div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20, fontSize: 13 }}>
              {search ? t('pool.no_match') : t('pool.empty_hint')}
            </div>
          ) : (
            CATEGORY_ORDER.map(cat => {
              const blocks = grouped[cat];
              if (!blocks || blocks.length === 0) return null;
              return (
                <div key={cat} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#666', marginBottom: 4, paddingLeft: 2 }}>
                    {t(`category.${cat}`)} ({blocks.length})
                  </div>
                  {blocks.map(b => {
                    const name = b.content?.name || b.content?.title || b.content?.card_name || '';
                    const color = BLOCK_COLORS[b.type] || '#999';
                    return (
                      <div key={b.id} style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        padding: '5px 8px', marginBottom: 3, borderRadius: 4,
                        background: 'var(--bg-card)', border: '1px solid var(--border-color)',
                        borderLeft: `3px solid ${color}`,
                        cursor: 'pointer', fontSize: 12,
                      }}
                        onClick={() => moveToCanvas(b)}
                        title={t('pool.click_to_place')}
                      >
                        <span style={{ fontSize: 10, color, fontWeight: 700, width: 14 }}>
                          {b.type.substring(0, 2)}
                        </span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: name ? 600 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {name || t(`block.${b.type}`)}
                          </div>
                          <div style={{ fontSize: 10, color: '#888' }}>
                            {t(`block.${b.type}`)} · {Math.round((b.completeness || 0) * 100)}%
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: 2 }}>
                          <span style={{ fontSize: 10, color: '#4A90D9', cursor: 'pointer' }}
                            onClick={(e) => { e.stopPropagation(); moveToCanvas(b); }}>📌</span>
                          <span style={{ fontSize: 10, color: '#E74C3C', cursor: 'pointer' }}
                            onClick={(e) => { e.stopPropagation(); deleteBlock(b.id); }}>🗑</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default BlockPoolPanel;
