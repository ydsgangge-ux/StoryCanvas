import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/projectStore';
import { useCanvasStore } from '../store/canvasStore';
import { useUIStore } from '../store/uiStore';
import { BLOCK_LABELS, BLOCK_COLORS, BLOCK_CATEGORIES, CATEGORY_LABELS } from '../types/blocks';
import { useT } from '../i18n/useT';

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
      showToast(`${BLOCK_LABELS[block.type] || block.type} 已放到画布`);
      await fetchPool();
      // 刷新画布
      const { blocks, connections } = useProjectStore.getState();
      syncFromBlocks(blocks, connections);
    } catch {
      showToast('操作失败', 'error');
    }
  };

  const deleteBlock = async (blockId: string) => {
    if (!confirm('确定删除此块？')) return;
    try {
      await fetch(`/api/projects/${currentProject!.id}/blocks/${blockId}`, { method: 'DELETE' });
      showToast('已删除');
      fetchPool();
    } catch {}
  };

  const filtered = poolBlocks.filter(b => {
    const label = BLOCK_LABELS[b.type] || '';
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
        <span>📦 块池</span>
        <button className="btn btn-sm btn-ghost" onClick={fetchPool} disabled={loading}>⟳</button>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        {/* 搜索 */}
        <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border-color)' }}>
          <input className="form-input" type="text" placeholder="🔍 搜索块类型或名称..."
            value={search} onChange={(e) => setSearch(e.target.value)}
            style={{ fontSize: 12, padding: '4px 8px' }} />
        </div>

        {/* 统计 */}
        <div style={{ padding: '4px 10px', fontSize: 11, color: '#888', borderBottom: '1px solid var(--border-color)' }}>
          共 {poolBlocks.length} 个块在池中
        </div>

        {/* 列表 */}
        <div style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto', padding: 8 }}>
          {loading ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20 }}>加载中...</div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#6c6c80', padding: 20, fontSize: 13 }}>
              {search ? '无匹配结果' : '块池为空\n创建新块时默认放入画布'}
            </div>
          ) : (
            CATEGORY_ORDER.map(cat => {
              const blocks = grouped[cat];
              if (!blocks || blocks.length === 0) return null;
              return (
                <div key={cat} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#666', marginBottom: 4, paddingLeft: 2 }}>
                    {CATEGORY_LABELS[cat] || cat} ({blocks.length})
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
                        title={`点击放到画布`}
                      >
                        <span style={{ fontSize: 10, color, fontWeight: 700, width: 14 }}>
                          {b.type.substring(0, 2)}
                        </span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: name ? 600 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {name || BLOCK_LABELS[b.type] || b.type}
                          </div>
                          <div style={{ fontSize: 10, color: '#888' }}>
                            {BLOCK_LABELS[b.type] || b.type} · {Math.round((b.completeness || 0) * 100)}%
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
