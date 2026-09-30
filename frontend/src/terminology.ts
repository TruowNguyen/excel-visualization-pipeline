import type { Entity } from './types';

export type EntityLevel = Entity['entity_level'] | null | undefined;

export type ComparisonTerminology = {
  title: string;
  description: string;
  selectorLabel: string;
  candidateNoun: string;
  candidatePlural: string;
  emptyMessage: string;
  noCandidateMessage: string;
  anchorLabel: string;
};

const LEVEL_LABELS: Record<string, string> = {
  project: 'Dự án',
  section: 'Nhóm vấn đề',
  item: 'Vấn đề',
  subitem: 'Tình trạng',
};

/** Remove only a leading structural number such as "1.1." from section labels. */
export function normalizeSectionDisplayLabel(rawLabel: string): string {
  const raw = String(rawLabel ?? '').trim();
  const match = raw.match(/^\d+(?:\.\d+)*\.\s+(.+)$/u);
  const normalized = match?.[1]?.trim();
  return normalized || raw;
}

export function getEntityDisplayName(entity: Pick<Entity, 'entity_label' | 'entity_level'>): string {
  const rawLabel = String(entity.entity_label ?? '').trim();
  return entity.entity_level === 'section' ? normalizeSectionDisplayLabel(rawLabel) : rawLabel;
}

export function getEntityLevelLabel(level: EntityLevel): string {
  return level ? LEVEL_LABELS[level] || 'Nội dung theo dõi' : 'Nội dung theo dõi';
}

export function getCurrentScopeLabel(level: EntityLevel): string {
  return ({
    project: 'Toàn dự án',
    section: 'Nhóm vấn đề đang chọn',
    item: 'Vấn đề đang xem',
    subitem: 'Tình trạng đang xem',
  } as Record<string, string>)[String(level)] || 'Nội dung đang chọn';
}

export function getChildrenScopeLabel(level: EntityLevel): string {
  return ({
    project: 'Các nhóm vấn đề trong dự án',
    section: 'Các vấn đề trong nhóm',
    item: 'Các tình trạng của vấn đề',
    subitem: 'Nội dung trực tiếp bên dưới',
  } as Record<string, string>)[String(level)] || 'Nội dung trực tiếp bên dưới';
}

export function getCurrentContextLabel(level: EntityLevel): string {
  return ({
    project: 'Dự án đang xem',
    section: 'Nhóm vấn đề đang xem',
    item: 'Vấn đề đang xem',
    subitem: 'Tình trạng đang xem',
  } as Record<string, string>)[String(level)] || 'Nội dung đang xem';
}

export function getSiblingLabel(level: EntityLevel): string {
  return ({
    section: 'các nhóm vấn đề trong cùng dự án',
    item: 'các vấn đề trong cùng nhóm',
    subitem: 'các tình trạng của cùng vấn đề',
  } as Record<string, string>)[String(level)] || 'các nội dung trong cùng nhóm';
}

export function getComparisonTerminology(level: EntityLevel): ComparisonTerminology {
  if (level === 'section') return {
    title: 'So sánh các nhóm vấn đề',
    description: 'Chỉ hiển thị các nhóm vấn đề thuộc cùng dự án với nhóm đang xem.',
    selectorLabel: 'Chọn thêm nhóm vấn đề để so sánh',
    candidateNoun: 'nhóm vấn đề',
    candidatePlural: 'nhóm vấn đề',
    emptyMessage: 'Chọn thêm một nhóm vấn đề trong cùng dự án để tạo biểu đồ.',
    noCandidateMessage: 'Không có nhóm vấn đề nào trong cùng dự án phù hợp để so sánh.',
    anchorLabel: 'Nhóm vấn đề đang xem',
  };
  if (level === 'item') return {
    title: 'So sánh các vấn đề trong cùng nhóm',
    description: 'Chỉ hiển thị các vấn đề thuộc cùng nhóm với vấn đề đang xem.',
    selectorLabel: 'Chọn thêm vấn đề để so sánh',
    candidateNoun: 'vấn đề',
    candidatePlural: 'vấn đề',
    emptyMessage: 'Chọn thêm một vấn đề trong cùng nhóm để tạo biểu đồ.',
    noCandidateMessage: 'Không có vấn đề nào trong cùng nhóm phù hợp để so sánh.',
    anchorLabel: 'Vấn đề đang xem',
  };
  if (level === 'subitem') return {
    title: 'So sánh các tình trạng của cùng vấn đề',
    description: 'Chỉ hiển thị các tình trạng thuộc cùng vấn đề với tình trạng đang xem.',
    selectorLabel: 'Chọn thêm tình trạng để so sánh',
    candidateNoun: 'tình trạng',
    candidatePlural: 'tình trạng',
    emptyMessage: 'Chọn thêm một tình trạng của cùng vấn đề để tạo biểu đồ.',
    noCandidateMessage: 'Không có tình trạng nào của cùng vấn đề phù hợp để so sánh.',
    anchorLabel: 'Tình trạng đang xem',
  };
  return {
    title: 'So sánh các nội dung trong cùng nhóm',
    description: 'Chỉ hiển thị các nội dung cùng loại và cùng nhóm với nội dung đang xem.',
    selectorLabel: 'Chọn thêm nội dung để so sánh',
    candidateNoun: 'nội dung',
    candidatePlural: 'nội dung',
    emptyMessage: 'Chọn thêm một nội dung trong cùng nhóm để tạo biểu đồ.',
    noCandidateMessage: 'Không có nội dung nào trong cùng nhóm phù hợp để so sánh.',
    anchorLabel: 'Nội dung đang xem',
  };
}

export function getEligibilityReasonMessage(reasonCode: string | null | undefined, level: EntityLevel): string {
  const terms = getComparisonTerminology(level);
  const noun = terms.candidateNoun;
  return ({
    UNIT_UNKNOWN: 'Chưa thể so sánh vì chưa xác định đơn vị đo.',
    UNIT_MISMATCH: `Không thể so sánh vì ${noun} này sử dụng đơn vị đo khác.`,
    ANCHOR_NO_VALUE: `${terms.anchorLabel} không có dữ liệu trong khoảng thời gian này.`,
    NO_METRIC_VALUE: `${getEntityLevelLabel(level)} này không có dữ liệu cho chỉ số đang chọn.`,
    RATE_NUMERATOR_MISSING: 'Có tỷ lệ nguồn nhưng thiếu số Báo sai/Lỗi, nên chưa thể tổng hợp tỷ lệ theo kỳ một cách chính xác.',
    STATISTIC_VALUE_MISSING: `${getEntityLevelLabel(level)} này không có giá trị thống kê cho chỉ số và phép tính đang chọn.`,
    NO_ELIGIBLE_DAYS: 'Không có ngày hợp lệ để tính trung bình mỗi ngày trong khoảng thời gian này.',
    DIRECT_TOTAL_REQUIRED: 'Chỉ số Tổng số chưa được ghi trực tiếp cho nội dung này; dữ liệu cấp trên chỉ dùng để xác định ngày hợp lệ.',
    NO_OVERLAPPING_PERIOD: 'Không có khoảng thời gian chung để so sánh.',
    NOT_SIBLING: level === 'section'
      ? 'Nhóm vấn đề này không thuộc cùng dự án.'
      : level === 'item'
        ? 'Vấn đề này không thuộc cùng nhóm.'
        : level === 'subitem'
          ? 'Tình trạng này không thuộc cùng vấn đề.'
          : 'Nội dung này không thuộc cùng nhóm.',
    LIMIT_REACHED: `Chỉ có thể so sánh tối đa 3 ${terms.candidatePlural}.`,
    STALE_DATA_VERSION: 'Dữ liệu mới đã được nhập. Kết quả đang xem vẫn thuộc phiên bản trước.',
  } as Record<string, string>)[String(reasonCode)] || 'Nội dung này chưa đáp ứng điều kiện so sánh.';
}

export function getComparisonButtonDescription(level: EntityLevel, available: boolean): string {
  const terms = getComparisonTerminology(level);
  return available
    ? `So sánh với ${getSiblingLabel(level)}`
    : `Không có ${terms.candidatePlural} phù hợp để so sánh`;
}
