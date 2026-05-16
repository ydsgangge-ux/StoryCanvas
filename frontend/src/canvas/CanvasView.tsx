import React, { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  Node,
  NodeTypes,
  Edge,
  Connection,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useCanvasStore } from '../store/canvasStore';
import { useProjectStore } from '../store/projectStore';
import { useUIStore } from '../store/uiStore';
import { BaseBlock, CharacterBlock, SceneBlock } from './nodes';
import ProgressBar from './overlays/ProgressBar';
import { useT } from '../i18n/useT';

const nodeTypes: NodeTypes = {
  default: BaseBlock,
  character: CharacterBlock,
  scene: SceneBlock,
};

const CONN_TYPES = [
  { value: 'causes', labelKey: 'conn.causes', descKey: 'conn.causes_desc' },
  { value: 'follows', labelKey: 'conn.follows', descKey: 'conn.follows_desc' },
  { value: 'parallels', labelKey: 'conn.parallels', descKey: 'conn.parallels_desc' },
  { value: 'foreshadows', labelKey: 'conn.foreshadows', descKey: 'conn.foreshadows_desc' },
  { value: 'resolves', labelKey: 'conn.resolves', descKey: 'conn.resolves_desc' },
  { value: 'contains', labelKey: 'conn.contains', descKey: 'conn.contains_desc' },
  { value: 'conflicts', labelKey: 'conn.conflicts', descKey: 'conn.conflicts_desc' },
  { value: 'influences', labelKey: 'conn.influences', descKey: 'conn.influences_desc' },
];

const CanvasView: React.FC = () => {
  const { t } = useT();
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, setSelectedBlock, syncFromBlocks, saveDirtyPositions } = useCanvasStore();
  const { currentProject, blocks, connections, progress } = useProjectStore();
  const { showToast, setShowBlockEditor, setShowWritingPanel } = useUIStore();
  const [pendingConnection, setPendingConnection] = useState<Connection | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: Node } | null>(null);
  const [edgeContextMenu, setEdgeContextMenu] = useState<{ x: number; y: number; edge: Edge } | null>(null);
  const [aiFillDialog, setAiFillDialog] = useState<{ blockId: string; hint: string } | null>(null);

  useEffect(() => {
    if (currentProject) {
      syncFromBlocks(blocks || [], connections || []);
    }
  }, [blocks, connections, currentProject]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedBlock(node.data);
    setShowBlockEditor(true);
  }, []);

  const onNodeDoubleClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedBlock(node.data);
    setShowBlockEditor(true);
  }, []);

  const onNodeContextMenu = useCallback((event: React.MouseEvent, node: Node) => {
    event.preventDefault();
    setContextMenu({ x: event.clientX, y: event.clientY, node });
  }, []);

  const onEdgeContextMenu = useCallback((event: React.MouseEvent, edge: Edge) => {
    event.preventDefault();
    setEdgeContextMenu({ x: event.clientX, y: event.clientY, edge });
  }, []);

  // 关闭右键菜单（块菜单 和 连线菜单）
  useEffect(() => {
    if (!contextMenu && !edgeContextMenu) return;
    const close = () => { setContextMenu(null); setEdgeContextMenu(null); };
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [contextMenu, edgeContextMenu]);

  const onPaneClick = useCallback(() => {
    setSelectedBlock(null);
    setShowBlockEditor(false);
  }, []);

  const onConnectHandler = useCallback((connection: Connection) => {
    if (connection.source && connection.target) {
      setPendingConnection(connection);
    }
  }, [currentProject]);

  /** 拖拽结束 → 直接通过 updateBlock API 保存该节点的位置 */
  const onNodeDragStop = useCallback(async (_event: React.MouseEvent, node: Node) => {
    if (!currentProject) return;
    try {
      const res = await fetch(`/api/projects/${currentProject.id}/blocks/${node.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ canvas_x: node.position.x, canvas_y: node.position.y }),
      });
      if (!res.ok) {
        showToast(t('canvas.position_save_failed'), 'error');
      }
    } catch {
      showToast(t('canvas.position_save_error'), 'error');
    }
  }, [currentProject, showToast]);

  const confirmConnection = (connType: string) => {
    if (pendingConnection?.source && pendingConnection?.target) {
      useProjectStore.getState().addConnection(currentProject?.id || '', {
        from_block: pendingConnection.source,
        to_block: pendingConnection.target,
        conn_type: connType,
      });
    }
    setPendingConnection(null);
  };

  return (
    <div className="canvas-wrapper">
      {/* Progress Bar */}
      {progress && (
        <ProgressBar
          overall={progress.overall}
          categories={progress.categories}
          status={progress.status}
          level={progress.level}
        />
      )}

      {/* Chapter Axis */}
      {currentProject && (
        <div className="chapter-axis">
          {Array.from({ length: Math.min(currentProject.chapter_count || 30, 50) }, (_, i) => (
            <div
              key={i}
              className="chapter-tick"
              style={{ left: `${100 + i * 100}px` }}
            >
              {i + 1}
            </div>
          ))}
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnectHandler}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        onNodeContextMenu={onNodeContextMenu}
        onEdgeContextMenu={onEdgeContextMenu}
        onNodeDragStop={onNodeDragStop}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        defaultEdgeOptions={{
          type: 'smoothstep',
          style: { stroke: '#666', strokeWidth: 2 },
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#333" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => node.data?.color || '#4A90D9'}
          maskColor="rgba(0, 0, 0, 0.7)"
          style={{ background: '#16213e' }}
        />
      </ReactFlow>

      {/* Connection Type Picker Modal */}
      {pendingConnection && (
        <div className="modal-overlay" onClick={() => setPendingConnection(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 400 }}>
            <div className="modal-header">
              <h3>{t('connection.select_title')}</h3>
              <button className="btn btn-sm btn-ghost" onClick={() => setPendingConnection(null)}>✕</button>
            </div>
            <div className="modal-body" style={{ padding: '12px 16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {CONN_TYPES.map((ct) => (
                  <button
                    key={ct.value}
                    className="btn"
                    style={{ textAlign: 'left', padding: '8px 12px', fontSize: 13 }}
                    onClick={() => confirmConnection(ct.value)}
                  >
                    <div style={{ fontWeight: 600 }}>{t(ct.labelKey)}</div>
                    <div style={{ fontSize: 11, color: '#888' }}>{t(ct.descKey)}</div>
                  </button>
                ))}
              </div>
              <button
                className="btn"
                style={{ width: '100%', marginTop: 8, color: '#E74C3C' }}
                onClick={() => setPendingConnection(null)}
              >
                ✕ {t('canvas.cancel_connection')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Right-click Context Menu (块) */}
      {contextMenu && (
        <div
          className="context-menu"
          style={{ position: 'fixed', left: contextMenu.x, top: contextMenu.y, zIndex: 1000 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="context-menu-item" onClick={() => {
            const { id, data: blockData } = contextMenu.node;
            setSelectedBlock(blockData);
            setShowBlockEditor(true);
            setContextMenu(null);
          }}>
            ✏️ {t('canvas.edit')}
          </div>
          <div className="context-menu-item" onClick={async () => {
            const { data: blockData } = contextMenu.node;
            setContextMenu(null);
            if (currentProject) {
              showToast(t('canvas.copying'));
              await useProjectStore.getState().addBlock(currentProject.id, {
                type: blockData.type,
                canvas_x: (blockData.canvas_x || 0) + 50,
                canvas_y: (blockData.canvas_y || 0) + 50,
                content: { ...(blockData.content || {}) },
              });
              showToast(t('canvas.copy'));
            }
          }}>
            📋 {t('canvas.copy')}
          </div>
          <div className="context-menu-item" onClick={async () => {
            const { id } = contextMenu.node;
            setContextMenu(null);
            if (currentProject) {
              try {
                await fetch(`/api/projects/${currentProject.id}/blocks/${id}/move-to-pool`, { method: 'POST' });
                await useProjectStore.getState().loadProject(currentProject.id);
                showToast(t('canvas.moved_to_pool'));
              } catch { showToast(t('canvas.operation_failed'), 'error'); }
            }
          }}>
            📦 {t('canvas.move_to_pool')}
          </div>
          <div className="context-menu-item" onClick={() => {
            const { id } = contextMenu.node;
            setAiFillDialog({ blockId: id, hint: '' });
            setContextMenu(null);
          }}>
            🤖 {t('canvas.ai_fill')}
          </div>
          <div className="context-menu-divider" />
          <div className="context-menu-item" style={{ color: '#E74C3C' }} onClick={async () => {
            const { id } = contextMenu.node;
            setContextMenu(null);
            if (currentProject) {
              showToast(t('canvas.deleting'));
              await useProjectStore.getState().removeBlock(currentProject.id, id);
              showToast(t('app.block_deleted'));
            }
          }}>
            🗑️ {t('canvas.delete')}
          </div>
        </div>
      )}

      {/* Right-click Context Menu (连线) */}
      {edgeContextMenu && (
        <div
          className="context-menu"
          style={{ position: 'fixed', left: edgeContextMenu.x, top: edgeContextMenu.y, zIndex: 1000 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div style={{ fontSize: 11, color: '#888', padding: '6px 12px 4px', borderBottom: '1px solid var(--border-color)' }}>
            🔗 {t(`conn.${edgeContextMenu.edge.data?.conn_type}`) || edgeContextMenu.edge.data?.conn_type || t('canvas.connection_label')}
          </div>
          <div className="context-menu-item" style={{ color: '#E74C3C' }} onClick={async () => {
            const { id } = edgeContextMenu.edge;
            setEdgeContextMenu(null);
            if (currentProject) {
              showToast(t('canvas.deleting_connection'));
              await useProjectStore.getState().removeConnection(currentProject.id, id);
              showToast(t('canvas.connection_deleted'));
            }
          }}>
            🗑️ {t('canvas.delete_connection')}
          </div>
        </div>
      )}

      {/* AI Fill Dialog */}
      {aiFillDialog && (
        <div className="modal-overlay" onClick={() => setAiFillDialog(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 400 }}>
            <div className="modal-header">
              <h3>🤖 {t('canvas.ai_fill_title')}</h3>
              <button className="btn btn-sm btn-ghost" onClick={() => setAiFillDialog(null)}>✕</button>
            </div>
            <div className="modal-body" style={{ padding: '12px 16px' }}>
              <textarea
                className="form-textarea"
                rows={4}
                value={aiFillDialog.hint}
                onChange={(e) => setAiFillDialog({ ...aiFillDialog, hint: e.target.value })}
                placeholder={t('canvas.ai_fill_placeholder')}
                style={{ width: '100%', marginBottom: 12 }}
              />
              <button
                className="btn btn-primary"
                style={{ width: '100%' }}
                onClick={async () => {
                  if (!currentProject) return;
                  showToast(t('canvas.ai_generating'));
                  const blockId = aiFillDialog.blockId;
                  const hint = aiFillDialog.hint;
                  setAiFillDialog(null);
                  try {
                    const res = await fetch(`/api/projects/${currentProject.id}/generate/block-content`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ block_id: blockId, field: 'all', hint }),
                    });
                    if (res.ok) {
                      const data = await res.json();
                      await useProjectStore.getState().updateBlock(currentProject.id, blockId, { content: data.merged_content });
                      showToast(t('canvas.ai_fill_complete'));
                    } else {
                      showToast(t('canvas.ai_fill_failed'), 'error');
                    }
                  } catch {
                    showToast(t('app.ai_fill_error'), 'error');
                  }
                }}
              >
                {t('editor.ai_generate')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CanvasView;
