/** Presentation-only emphasis. Never interpret HTML/Markdown from a model. */
const escapeText = (text: string): string => text.replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[character]!));

type Emphasis = { start: number; end: number; role: string };

export type InsightParagraph = { text: string; source?: string; startLabel?: string; endLabel?: string };

export function renderInsightParagraph(paragraph: InsightParagraph, showSource = true): string {
  return `<p>${renderInsightText(paragraph.text)}${showSource && paragraph.source === 'deterministic'
    ? '<small class="ai-paragraph-source">Tổng hợp từ số liệu</small>' : ''}</p>`;
}

export function renderInsightPhase(phase: InsightParagraph, showSource = true): string {
  const label = phase.startLabel === phase.endLabel ? phase.startLabel
    : [phase.startLabel, phase.endLabel].filter(Boolean).join(' → ');
  return `<li>${label ? `<h5>${escapeText(label)}</h5>` : ''}${renderInsightParagraph(phase, showSource)}</li>`;
}

export function renderInsightText(text: string): string {
  const spans: Emphasis[] = [];
  const topic = /^(.+? · (?:Tổng trong kỳ|Trung bình\/ngày)):\s*/.exec(text);
  const offset = topic ? topic[0].length : 0;
  if (topic) spans.push({ start: 0, end: topic[1].length + 1, role: 'topic' });
  const body = text.slice(offset);
  const add = (match: RegExpExecArray | null, role: string, group = 0): void => {
    if (!match) return;
    const start = offset + match.index + (group ? match[0].indexOf(match[group]) : 0);
    spans.push({ start, end: start + match[group].length, role });
  };
  // One named subject, one meaningful movement, up to two absolute deltas.
  // Dates, endpoint levels and relative percentages remain ordinary text.
  if (!topic) add(/Tổng báo sai \(lỗi\)|Báo sai\/Lỗi|Số lỗi|Tổng số(?: ghi nhận)?|Tỷ lệ báo sai|% báo sai/i.exec(body), 'subject');
  const delta = /chênh lệch(?: đầu–cuối)?\s*:?\s*([-+]?\d+(?:[.,]\d+)*)/gi;
  for (let count = 0, match; count < 2 && (match = delta.exec(body)); count++) add(match, 'delta', 1);
  if (spans.filter(span => span.role !== 'topic').length < 3) {
    add(/không (?:đồng nghĩa|có nghĩa) (?:có nhiều lỗi hơn|số lỗi tăng|tỷ lệ báo sai tăng)|không duy trì đà tăng|tăng rồi giảm|giảm rồi tăng|giảm liên tiếp|tăng liên tiếp|giữ nguyên(?: ở (?:hai )?kỳ cuối)?|đổi chiều/i.exec(body), 'movement');
  }
  spans.sort((left, right) => left.start - right.start);
  let cursor = 0;
  let output = '';
  for (const span of spans) {
    if (span.start < cursor) continue;
    output += escapeText(text.slice(cursor, span.start));
    output += `<strong class="ai-emphasis ai-emphasis-${span.role}">${escapeText(text.slice(span.start, span.end))}</strong>`;
    cursor = span.end;
  }
  return output + escapeText(text.slice(cursor));
}
