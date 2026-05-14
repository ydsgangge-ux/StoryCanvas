export async function exportFull(projectId: string, includeDrafts: boolean = false) {
  const url = `/api/projects/${projectId}/export/full?include_drafts=${includeDrafts}`;
  window.open(url, '_blank');
}

export async function exportCanvasJson(projectId: string, includeDrafts: boolean = false) {
  const url = `/api/projects/${projectId}/export/canvas-json?include_drafts=${includeDrafts}`;
  window.open(url, '_blank');
}

export async function exportMarkdown(projectId: string) {
  const url = `/api/projects/${projectId}/export/markdown`;
  window.open(url, '_blank');
}

export interface ImportPreview {
  filename: string;
  format: string;
  title: string;
  storycanvas_version?: string;
  total_blocks: number;
  total_chapters: number;
  total_words: number;
  story_cards?: string[];
  exported_at?: string;
}

export async function importPreview(file: File): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/api/projects/import/preview', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '导入预览失败' }));
    throw new Error(err.detail || '导入预览失败');
  }
  return res.json();
}

export async function importProject(file: File, asNew: boolean = true): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`/api/projects/import?as_new=${asNew}`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '导入失败' }));
    throw new Error(err.detail || '导入失败');
  }
  return res.json();
}
