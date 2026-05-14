export async function generateOutline(
  projectId: string,
  chapterNum: number,
  additionalInstructions: string = '',
  onChunk: (text: string) => void,
  onDone: (outline: string) => void,
  onError: (msg: string) => void
): Promise<void> {
  const response = await fetch(`/api/projects/${projectId}/generate/chapter-outline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chapter_num: chapterNum, additional_instructions: additionalInstructions }),
  });

  if (!response.ok) {
    onError('生成请求失败');
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError('无法读取响应流');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';
  let outline = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        let dataStr = line.slice(6).trim();
        if (dataStr.startsWith('{')) {
          try {
            const data = JSON.parse(dataStr);
            if (data.event === 'chunk' && data.data) {
              if (data.data.text) {
                outline += data.data.text;
                onChunk(data.data.text);
              }
            } else if (data.event === 'done' && data.data) {
              onDone(data.data.outline || outline);
            } else if (data.event === 'error' && data.data) {
              onError(data.data.msg);
            }
          } catch {
            // incomplete JSON, continue buffering
          }
        }
      }
    }
  }

  if (outline) onDone(outline);
}

export async function generateChapterContent(
  projectId: string,
  chapterNum: number,
  outlineConfirmed: boolean = true,
  onStage: (stage: string, msg: string) => void,
  onChunk: (text: string) => void,
  onDone: (result: any) => void,
  onError: (msg: string) => void,
  onWarning: (violations: any[]) => void,
  blockId?: string  // 可选：指定 CHAPTER_DETAIL 块ID作为写作来源
): Promise<void> {
  const response = await fetch(`/api/projects/${projectId}/generate/chapter-content`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chapter_num: chapterNum, outline_confirmed: outlineConfirmed, block_id: blockId }),
  });

  if (!response.ok) {
    onError('生成请求失败');
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError('无法读取响应流');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6).trim());
          if (data.event === 'stage' && data.data) {
            onStage(data.data.stage, data.data.msg);
          } else if (data.event === 'chunk' && data.data) {
            if (data.data.text) onChunk(data.data.text);
          } else if (data.event === 'warning' && data.data) {
            if (data.data.violations) onWarning(data.data.violations);
          } else if (data.event === 'done' && data.data) {
            onDone(data.data);
          } else if (data.event === 'error' && data.data) {
            onError(data.data.msg);
          }
        } catch {
          // continue
        }
      }
    }
  }
}
