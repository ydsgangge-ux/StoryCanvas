import React, { useEffect, useState } from 'react';
import * as snapshotsApi from '../api/snapshots';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore'
import { useT } from '../i18n/useT';;

interface SnapshotHistoryPanelProps {
  onClose: () => void;
}

const SnapshotHistoryPanel: React.FC<SnapshotHistoryPanelProps> = ({ onClose }) => {
  const { currentProject } = useProjectStore();
  const { showToast } = useUIStore();
  const [snapshots, setSnapshots] = useState<snapshotsApi.SnapshotItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCheckpointLabel, setNewCheckpointLabel] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [restoring, setRestoring] = useState<string | null>(null);

  useEffect(() => {
    if (currentProject) loadSnapshots();
  }, [currentProject?.id]);

  const loadSnapshots = async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const data = await snapshotsApi.getSnapshots(currentProject.id);
      setSnapshots(data);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
    setLoading(false);
  };

  const handleCreateCheckpoint = async () => {
    if (!currentProject || !newCheckpointLabel.trim()) return;
    try {
      await snapshotsApi.createCheckpoint(currentProject.id, newCheckpointLabel.trim());
      showToast(`检查点已保存: ${newCheckpointLabel}`);
      setNewCheckpointLabel('');
      setShowCreateForm(false);
      loadSnapshots();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const handleRestore = async (snapId: string, label: string) => {
    if (!currentProject) return;
    if (!confirm(`确定要回滚到「${label || '此版本'}」？\n当前状态将自动备份。`)) return;
    setRestoring(snapId);
    try {
      await snapshotsApi.restoreSnapshot(currentProject.id, snapId);
      showToast(`已回滚到: ${label || '快照'}`);
      // Reload project
      const { loadProject } = useProjectStore.getState();
      await loadProject(currentProject.id);
    } catch (e: any) {
      showToast(e.message, 'error');
    }
    setRestoring(null);
  };

  const handleDelete = async (snapId: string) => {
    if (!currentProject) return;
    if (!confirm('确定要删除此检查点？')) return;
    try {
      await snapshotsApi.deleteSnapshot(currentProject.id, snapId);
      showToast('检查点已删除');
      loadSnapshots();
    } catch (e: any) {
      showToast(e.message, 'error');
    }
  };

  const checkpoints = snapshots.filter((s) => s.snapshot_type === 'checkpoint');
  const autoSnapshots = snapshots.filter((s) => s.snapshot_type === 'auto');

  return (
    <div className="panel" style={{ width: 340, minWidth: 340 }}>
      <div className="panel-header">
        <span>⏱ 历史</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn btn-sm" onClick={() => setShowCreateForm(!showCreateForm)}>
            📸 检查点
          </button>
          <button className="btn btn-sm btn-ghost" onClick={onClose}>✕</button>
        </div>
      </div>
      <div className="panel-body" style={{ padding: '8px 12px' }}>
        {/* Create checkpoint form */}
        {showCreateForm && (
          <div style={{ marginBottom: 12, padding: 8, background: 'var(--bg-primary)', borderRadius: 6 }}>
            <label className="form-label">检查点名称</label>
            <div style={{ display: 'flex', gap: 4 }}>
              <input
                className="form-input"
                value={newCheckpointLabel}
                onChange={(e) => setNewCheckpointLabel(e.target.value)}
                placeholder="如：第一幕完成"
                onKeyDown={(e) => e.key === 'Enter' && handleCreateCheckpoint()}
                style={{ flex: 1 }}
                autoFocus
              />
              <button className="btn btn-sm btn-primary" onClick={handleCreateCheckpoint}>保存</button>
            </div>
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: 20, color: '#6c6c80' }}>
            <span className="loading-spinner" /> 加载中...
          </div>
        ) : snapshots.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 20, color: '#6c6c80', fontSize: 13 }}>
            暂无快照。<br />点击「📸 检查点」创建第一个里程碑。
          </div>
        ) : (
          <>
            {/* Checkpoints */}
            {checkpoints.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#FFD700', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
                  📌 检查点（永久）
                </div>
                {checkpoints.map((s) => (
                  <SnapshotItem
                    key={s.id}
                    snapshot={s}
                    onRestore={() => handleRestore(s.id, s.label || '未命名')}
                    onDelete={() => handleDelete(s.id)}
                    isRestoring={restoring === s.id}
                  />
                ))}
              </div>
            )}

            {/* Auto snapshots */}
            {autoSnapshots.length > 0 && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#4A90D9', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
                  🕐 自动保存（最近{autoSnapshots.length}个）
                </div>
                {autoSnapshots.map((s) => (
                  <SnapshotItem
                    key={s.id}
                    snapshot={s}
                    onRestore={() => handleRestore(s.id, s.label || `自动保存 ${formatTime(s.created_at)}`)}
                    isRestoring={restoring === s.id}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

interface SnapshotItemProps {
  snapshot: snapshotsApi.SnapshotItem;
  onRestore: () => void;
  onDelete?: () => void;
  isRestoring: boolean;
}

const SnapshotItem: React.FC<SnapshotItemProps> = ({ snapshot, onRestore, onDelete, isRestoring }) => {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="tracking-item" style={{ position: 'relative', cursor: 'default' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 500, color: '#e0e0e0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {snapshot.label || (snapshot.snapshot_type === 'auto' ? '自动保存' : '未命名检查点')}
        </div>
        <div style={{ fontSize: 10, color: '#6c6c80' }}>
          {formatTime(snapshot.created_at)}
          {snapshot.block_count > 0 && ` · ${snapshot.block_count}个块`}
          {snapshot.word_count > 0 && ` · ${snapshot.word_count}字`}
        </div>
      </div>
      <button
        className="btn btn-sm btn-ghost"
        onClick={() => setShowMenu(!showMenu)}
        style={{ fontSize: 14 }}
      >
        ⋯
      </button>

      {showMenu && (
        <>
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 10 }}
            onClick={() => setShowMenu(false)} />
          <div style={{
            position: 'absolute', right: 4, top: 28, zIndex: 11,
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: 6, padding: 4, minWidth: 120, boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
          }}>
            <div className="menu-item" onClick={() => { setShowMenu(false); onRestore(); }}
              style={{ padding: '6px 10px', cursor: 'pointer', borderRadius: 4, fontSize: 12 }}>
              {isRestoring ? '回滚中...' : '↩ 回滚到此版本'}
            </div>
            {snapshot.snapshot_type === 'checkpoint' && onDelete && (
              <div className="menu-item" onClick={() => { setShowMenu(false); onDelete(); }}
                style={{ padding: '6px 10px', cursor: 'pointer', borderRadius: 4, fontSize: 12, color: '#E74C3C' }}>
                🗑 删除
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

function formatTime(isoStr: string): string {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hour = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${month}-${day} ${hour}:${min}`;
  } catch {
    return isoStr.substring(0, 16);
  }
}

export default SnapshotHistoryPanel;
